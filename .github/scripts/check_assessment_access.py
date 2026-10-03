#!/usr/bin/env python3
"""Performance Assessment Agent Access Guard.

Ensures that files inside 'backend/app/agents/performance_assessment/'
can only be modified by authorized maintainer (Sadeesha Sathsara).
If modified by any other author, it sends alert emails to Sadeesha
and the contributor, prints a prominent blocker message, and fails the CI.
"""

import os
import sys
import smtplib
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Tuple, Set


# Protected folder can be overridden via PROTECTED_PATH secret/env var
PROTECTED_PATH = os.environ.get("PROTECTED_PATH") or "backend/app/agents/performance_assessment"


def get_authorized_identities() -> Tuple[Set[str], Set[str]]:
    """Loads authorized GitHub usernames and commit author emails from secrets/environment."""
    users = set()
    emails = set()

    env_users = os.environ.get("AUTHORIZED_USERS", "")
    if env_users:
        for u in env_users.split(","):
            if u.strip():
                users.add(u.strip().lower())
    else:
        users.add("sadeeshasathsara")

    env_emails = os.environ.get("AUTHORIZED_EMAILS", "")
    if env_emails:
        for e in env_emails.split(","):
            if e.strip():
                emails.add(e.strip().lower())

    sadeesha_email = os.environ.get("SADEESHA_EMAIL", "")
    if sadeesha_email:
        for e in sadeesha_email.split(","):
            if e.strip():
                emails.add(e.strip().lower())

    # Fallback defaults if no secret is provided yet
    if not emails:
        emails.update({
            "sadeeshasathsara99@gmail.com",
            "sathsarakumbukage@gmail.com",
        })

    return users, emails


def get_changed_files_and_authors() -> List[Tuple[str, str, str, str]]:
    """Returns list of (commit_hash, author_name, author_email, changed_file)."""
    records = []
    base_sha = os.environ.get("BASE_SHA")
    head_sha = os.environ.get("HEAD_SHA") or "HEAD"

    if base_sha and not base_sha.startswith("0000000"):
        rev_range = f"{base_sha}..{head_sha}"
    else:
        rev_range = "-1"

    try:
        cmd = [
            "git",
            "log",
            rev_range,
            "--name-only",
            "--format=COMMIT:%H|%an|%ae",
            "--",
            PROTECTED_PATH,
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[INFO] Running single commit inspection for protected path: {e}")
        cmd = [
            "git",
            "log",
            "-1",
            "--name-only",
            "--format=COMMIT:%H|%an|%ae",
            "--",
            PROTECTED_PATH,
        ]
        out = subprocess.check_output(cmd, text=True)

    current_commit = ""
    current_author_name = ""
    current_author_email = ""

    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("COMMIT:"):
            parts = line[7:].split("|")
            current_commit = parts[0] if len(parts) > 0 else ""
            current_author_name = parts[1] if len(parts) > 1 else ""
            current_author_email = parts[2] if len(parts) > 2 else ""
        else:
            if PROTECTED_PATH in line.replace("\\", "/"):
                records.append(
                    (current_commit, current_author_name, current_author_email, line)
                )

    return records


def send_email_alert(
    unauthorized_authors: List[Tuple[str, str]],
    changed_files: List[str],
    github_actor: str,
    pr_url: str,
) -> bool:
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port_raw = os.environ.get("SMTP_PORT", "587")
    smtp_user = os.environ.get("SMTP_USERNAME")
    smtp_pass = os.environ.get("SMTP_PASSWORD")

    if not (smtp_host and smtp_user and smtp_pass):
        print("\n[NOTICE] SMTP credentials (SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD) not configured in GitHub Secrets.")
        print("[NOTICE] Email notification was skipped, but access guard will still block the pull request.\n")
        return False

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = 587

    smtp_from = os.environ.get("SMTP_FROM_EMAIL") or smtp_user

    # Maintainer recipients (Sadeesha's email accounts)
    maintainer_emails = set()
    sadeesha_email_raw = os.environ.get("SADEESHA_EMAIL", "")
    if sadeesha_email_raw:
        for e in sadeesha_email_raw.split(","):
            if e.strip():
                maintainer_emails.add(e.strip().lower())

    auth_emails_raw = os.environ.get("AUTHORIZED_EMAILS", "")
    if auth_emails_raw:
        for e in auth_emails_raw.split(","):
            if e.strip():
                maintainer_emails.add(e.strip().lower())

    if not maintainer_emails:
        maintainer_emails.update({
            "sadeeshasathsara99@gmail.com",
            "sathsarakumbukage@gmail.com",
        })

    recipients = set(maintainer_emails)
    for name, email in unauthorized_authors:
        if email and "@" in email and "users.noreply.github.com" not in email:
            recipients.add(email.strip().lower())

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[BLOCKED] Unauthorized changes to Assessment Agent by {github_actor or 'Contributor'}"
    msg["From"] = f"Assessment Agent Guard <{smtp_from}>"
    msg["To"] = ", ".join(recipients)

    authors_summary = "\n".join([f"- {name} <{email}>" for name, email in unauthorized_authors])
    files_summary = "\n".join([f"- {f}" for f in set(changed_files)])

    text_body = f"""ALERT: Unauthorized modification to Performance Assessment Agent

GitHub Actor: {github_actor or 'Unknown'}
PR / Branch: {pr_url or 'Direct Push'}

Unauthorized Commit Authors:
{authors_summary}

Protected Files Changed:
{files_summary}

NOTICE FOR CONTRIBUTOR:
ask sadeesha sathsara before merged, you have changed the code inside assessment agent.
Under the folder '{PROTECTED_PATH}', code can only be changed by Sadeesha Sathsara.
Please sync with Sadeesha Sathsara to coordinate modifications.
"""

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e1e4e8; border-radius: 8px; padding: 24px;">
          <h2 style="color: #cf222e; border-bottom: 2px solid #cf222e; padding-bottom: 8px;">
            [BLOCKED] Unauthorized Changes to Assessment Agent
          </h2>
          <p><strong>GitHub User:</strong> <code>{github_actor or 'Unknown'}</code></p>
          <p><strong>Reference / PR:</strong> <a href="{pr_url}">{pr_url or 'Direct Push'}</a></p>
          
          <h3 style="color: #24292f;">Commit Authors Detected:</h3>
          <pre style="background: #f6f8fa; padding: 12px; border-radius: 6px;">{authors_summary}</pre>

          <h3 style="color: #24292f;">Protected Files Modified:</h3>
          <pre style="background: #f6f8fa; padding: 12px; border-radius: 6px;">{files_summary}</pre>

          <div style="background: #fff8c5; border-left: 4px solid #bf8700; padding: 12px; margin-top: 16px;">
            <strong>Notice:</strong> <em>ask sadeesha sathsara before merged, you have changed the code inside assessment agent.</em>
            <br>
            Files under <code>{PROTECTED_PATH}</code> are strictly restricted to Sadeesha Sathsara.
          </div>
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, list(recipients), msg.as_string())
        server.quit()
        print(f"[INFO] Alert email successfully sent to: {', '.join(recipients)}")
        return True
    except Exception as exc:
        print(f"[ERROR] Failed to send alert email: {exc}")
        return False


def main():
    auth_users, auth_emails = get_authorized_identities()
    github_actor = os.environ.get("GITHUB_ACTOR", "").strip().lower()

    records = get_changed_files_and_authors()
    if not records:
        print(f"[OK] No changes detected inside protected path: '{PROTECTED_PATH}'.")
        sys.exit(0)

    unauthorized_authors = []
    unauthorized_files = []

    for commit, author_name, author_email, file_path in records:
        email_clean = author_email.strip().lower()
        is_author_auth = email_clean in auth_emails
        is_actor_auth = (github_actor in auth_users) if github_actor else True

        # Must be authorized by both GitHub account and commit author
        if not is_author_auth or not is_actor_auth:
            unauthorized_authors.append((author_name, author_email))
            unauthorized_files.append(file_path)

    if not unauthorized_authors:
        print(f"[OK] Changes inside '{PROTECTED_PATH}' were authorized by maintainer: Sadeesha Sathsara.")
        sys.exit(0)

    unique_authors = list({(name, email) for name, email in unauthorized_authors})
    unique_files = sorted(list(set(unauthorized_files)))

    pr_url = os.environ.get("PR_URL", "")

    # Print GitHub Actions workflow command to render annotation on PR
    print("::error title=Unauthorized Modification::ask sadeesha sathsara before merged, you have changed the code inside assessment agent.")

    banner = "=" * 80
    print(f"\n{banner}")
    print("[ERROR] CI GUARD FAILURE: UNAUTHORIZED MODIFICATION DETECTED")
    print(banner)
    print("ask sadeesha sathsara before merged, you have changed the code inside assessment agent.")
    print(f"\nProtected Folder: {PROTECTED_PATH}")
    print(f"GitHub Actor:     {github_actor or 'Unknown'}")
    print("\nUnauthorized Committer(s):")
    for name, email in unique_authors:
        print(f"  - {name} <{email}>")
    print("\nModified Files:")
    for f in unique_files:
        print(f"  - {f}")
    print(f"{banner}\n")

    send_email_alert(unique_authors, unique_files, github_actor, pr_url)

    sys.exit(1)


if __name__ == "__main__":
    main()
