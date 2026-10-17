# Keycloak: sign-in, sign-up and email

Keycloak handles who a person is: email and password, Google, Microsoft and GitHub, email
verification and password reset. The app and the Core API never see a password. What a person
**is** in SELVIA (student or lecturer) is chosen in the app after the first sign-in and stored in
the Core API database; see `docs/REGISTRATION_AND_TEAMS.md`.

| File | What it is |
| --- | --- |
| `realm-export.json` | The realm as it is created the **first** time Keycloak starts |
| `configure_realm.py` | Applies email, social sign-in and the account-linking flow to a realm that is **already running** (safe to repeat) |
| `providers-src/link-by-email-code/` | The Keycloak plugin that links a provider sign-in to an existing account with an emailed code (Java, with unit tests) |
| `build_provider.py` | Builds that plugin with Docker and puts the jar in `providers/` (not committed) |
| `themes/mentor/login/` | The sign-in, sign-up and password pages |
| `themes/mentor/email/` | The look and wording of the emails Keycloak sends |

Keycloak reads `realm-export.json` only when the realm does not exist. Editing it later changes
nothing on a running realm, which is why `configure_realm.py` exists.

---

## 1. Set it up

### Start Keycloak

From the repository root, as described in `docs/ENVIRONMENT_GUIDE.md`:

```bash
docker compose --profile infra up -d
```

### Configure email

Keycloak needs a mail server for verification and password-reset emails. **Until it has one,
nobody can finish registering**, because the link to verify an address cannot be sent.

Add these to the `.env` in the repository root (never commit it):

```bash
KC_SMTP_HOST=smtp.example.com
KC_SMTP_PORT=587
KC_SMTP_SECURITY=starttls        # starttls (587), ssl (465) or none
KC_SMTP_USER=...
KC_SMTP_PASSWORD=...
KC_SMTP_FROM=no-reply@yourdomain.example
KC_SMTP_FROM_NAME=SELVIA
```

Any SMTP provider works: Brevo, Postmark, Amazon SES, Mailgun, or a Gmail account with an app
password. Use the same provider for the Core API (`backend/server/.env.example`, "Email").
Sending from your own domain needs the provider's SPF and DKIM records, or mail lands in spam.

For development, use Mailpit instead (nothing is delivered, you read it in a web page):

```bash
docker compose --profile dev up -d mailpit      # inbox on http://localhost:8025
# KC_SMTP_HOST=host.docker.internal  KC_SMTP_PORT=1025  KC_SMTP_SECURITY=none
# KC_SMTP_FROM=no-reply@selvia.local
```

### Add Google, Microsoft and GitHub (optional)

Each provider needs an OAuth app, which you create in the provider's console. The script prints
the exact **redirect URI** to register; it has this shape:

```text
https://<your-keycloak-host>/auth/realms/mentor/broker/<google|microsoft|github>/endpoint
```

| Provider | Where to create the app | Notes |
| --- | --- | --- |
| Google | Google Cloud Console, APIs and Services, Credentials, OAuth client ID (Web application) | Add the redirect URI under "Authorized redirect URIs" |
| Microsoft | Azure portal, Microsoft Entra ID, App registrations | Supported account types: "Accounts in any organizational directory and personal Microsoft accounts". Set `MICROSOFT_TENANT=common` unless you restrict it |
| GitHub | GitHub, Settings, Developer settings, OAuth Apps | The callback URL is the redirect URI |

Then add the credentials to the same `.env` (a provider is skipped when its pair is missing):

```bash
GOOGLE_CLIENT_ID=...        GOOGLE_CLIENT_SECRET=...
MICROSOFT_CLIENT_ID=...     MICROSOFT_CLIENT_SECRET=...     # MICROSOFT_TENANT=common
GITHUB_CLIENT_ID=...        GITHUB_CLIENT_SECRET=...
```

The sign-in page lists only the providers that are configured.

### Tell Keycloak where the web app is

Keycloak only sends people back to addresses it knows. List them, comma separated:

```bash
FRONTEND_URLS=http://localhost:5173,https://app.yourdomain.example
```

### Apply it

```bash
python docker/keycloak/configure_realm.py --dry-run     # shows the changes, secrets hidden
python docker/keycloak/configure_realm.py               # applies them
```

It finds the running Keycloak container by name (use `--container NAME` if there are several),
reads the `.env` above, and:

- sets the theme, email as the username, brute-force protection and a 10 character password policy;
- stores the mail server and **then** turns on email verification (it will not turn it on without a mail server);
- creates or updates each configured provider;
- sets the web app's addresses and turns off direct password grants.

Run it again whenever you change the `.env`. It never deletes anything.

---

## 2. How accounts behave

- **Email is the username.** One account per address (`duplicateEmailsAllowed` is off).
- **Verified email.** The Core API only matches team invitations to an account whose address
  Keycloak has verified (`email_verified` in the token).
- **Google** addresses are trusted as verified. **Microsoft and GitHub** are not: a Microsoft
  tenant administrator can set any address on an account, and a GitHub address can be changed, so
  those people confirm their address by email once. Trusting them would let someone create a
  provider account with a victim's address and take over the victim's SELVIA account.
- **Same address, different provider.** If a provider sign-in uses an address that already has an
  account, the person is **not** let in and nothing can be edited. They see who is signing in
  (the provider's name, picture and email) and which account it would join, press *Send code*,
  and must enter the 6 digit code emailed to the account's address. Only then are the two linked,
  and the address counts as verified. See section 4.
- **Locking out.** Five failed sign-ins in a row wait one minute, then longer, up to 15 minutes.

## 3. Changing the pages

The theme follows `frontend/src/index.css` (colours, radius, Geist font), so sign-in matches the
app. Edit the `.ftl` files and `resources/css/styles.css`.

Keycloak caches theme files. In the Docker setup a restart is enough (the cache is kept in
memory, see `docker-compose.yml`). To see changes without restarting while you work, run a local
Keycloak with `start-dev`, which turns the caches off:

```bash
docker run --rm -p 8085:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin \
  -e KC_HTTP_RELATIVE_PATH=/auth \
  -v "$PWD/docker/keycloak/themes:/opt/keycloak/themes:ro" \
  -v "$PWD/docker/keycloak/realm-export.json:/opt/keycloak/data/import/realm-export.json:ro" \
  quay.io/keycloak/keycloak:24.0 start-dev --import-realm
```

## 4. Linking accounts by emailed code

Keycloak 24 can only confirm a link with an emailed *link*, not a code, so SELVIA ships a small
plugin: `providers-src/link-by-email-code`. `configure_realm.py` builds a copy of Keycloak's
"first broker login" flow called **selvia first broker login** and points the providers at it:

```text
Review Profile                      off (the person cannot edit anything)
User creation or linking
  Create User If Unique             a new person gets an account as before
  Handle Existing Account
    SELVIA: link by emailed code    profile shown read only -> code emailed -> link
```

The code is 6 digits, valid for 10 minutes, with 5 tries; a wrong code is counted, three emails at
most are sent per sign-in and one a minute. Only a salted hash of the code is kept, in the login
session. The code goes to the **existing account's** address, so only the owner of that mailbox
can link.

**Install it** (needs Docker; do this on the server too):

```bash
python docker/keycloak/build_provider.py        # builds the jar and runs its unit tests
docker compose --profile infra up -d --no-deps keycloak   # picks up the providers folder
python docker/keycloak/configure_realm.py       # creates the flow and points the providers at it
```

The script refuses to touch the providers if the plugin is not loaded, so a missing jar cannot
leave sign-in broken. To go back, set a provider's *First login flow* to "first broker login" in
the admin console.

The pages are `themes/mentor/login/link-account.ftl` and `link-account-code.ftl`; the email is
`themes/mentor/email/{html,text}/link-code.ftl`.

---

## 5. If something is wrong

| Symptom | Cause |
| --- | --- |
| "Failed to send email" when registering | No mail server, or wrong `KC_SMTP_*`. Check with Mailpit first |
| Everyone is "email not verified" in the app | Verification is off, or the realm was imported before this change: run `configure_realm.py` |
| A provider button is missing | Its `*_CLIENT_ID` / `*_CLIENT_SECRET` pair is not set, or `configure_realm.py` was not run after setting it |
| Sign-up shows a username field and no steps | Keycloak is running an older copy of the theme: pull and restart it |
| The terms box has no link | Set `termsUrl=https://...` in `themes/mentor/login/theme.properties` |
| "Invalid redirect_uri" | The web app's address is missing from `FRONTEND_URLS` |
| Provider says redirect URI mismatch | The URI registered with the provider differs from the one the script printed |
| Old styles after changing the theme | Restart Keycloak (the gzip cache lives in memory and is emptied) |
| "The link-by-code plugin is not installed" | Run `build_provider.py` and recreate the Keycloak container, then run the script again |
| The link page says the email could not be sent | Keycloak has no working mail server (`KC_SMTP_*`, then `configure_realm.py`) |
| A provider sign-in shows "Update Account Information" with editable fields | The provider still uses Keycloak's own flow: run `configure_realm.py` |
