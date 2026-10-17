package org.selvia.keycloak;

import jakarta.ws.rs.core.MultivaluedMap;
import jakarta.ws.rs.core.Response;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import org.jboss.logging.Logger;
import org.keycloak.authentication.AuthenticationFlowContext;
import org.keycloak.authentication.authenticators.broker.AbstractIdpAuthenticator;
import org.keycloak.authentication.authenticators.broker.util.SerializedBrokeredIdentityContext;
import org.keycloak.broker.provider.BrokeredIdentityContext;
import org.keycloak.email.EmailException;
import org.keycloak.email.EmailTemplateProvider;
import org.keycloak.events.Errors;
import org.keycloak.forms.login.LoginFormsProvider;
import org.keycloak.models.UserModel;
import org.keycloak.sessions.AuthenticationSessionModel;

/**
 * Links a social or enterprise login to an account that already exists, but only for the person
 * who owns that account's mailbox.
 *
 * It replaces the "confirm link" and "verify existing account" steps of the first broker login:
 *   1. show who is signing in (name, picture and email from the provider, nothing editable) and
 *      what will be linked;
 *   2. email a six digit code to the existing account's address;
 *   3. link only when the code is entered correctly.
 *
 * A wrong code is counted, a code expires, and the number of emails is limited (CodeChallenge).
 */
public class LinkByEmailCodeAuthenticator extends AbstractIdpAuthenticator {

    private static final Logger LOG = Logger.getLogger(LinkByEmailCodeAuthenticator.class);
    private static final String NOTE = "selvia.link.code";
    private static final SecureRandom RANDOM = new SecureRandom();

    private static final String PROFILE_PAGE = "link-account.ftl";
    private static final String CODE_PAGE = "link-account-code.ftl";

    @Override
    protected void authenticateImpl(
            AuthenticationFlowContext context,
            SerializedBrokeredIdentityContext serializedCtx,
            BrokeredIdentityContext brokerContext) {
        CodeChallenge challenge = CodeChallenge.parse(context.getAuthenticationSession().getAuthNote(NOTE));
        context.challenge(challenge == null
                ? profilePage(context, brokerContext, null)
                : codePage(context, brokerContext, challenge, null));
    }

    @Override
    protected void actionImpl(
            AuthenticationFlowContext context,
            SerializedBrokeredIdentityContext serializedCtx,
            BrokeredIdentityContext brokerContext) {
        AuthenticationSessionModel session = context.getAuthenticationSession();
        MultivaluedMap<String, String> form = context.getHttpRequest().getDecodedFormParameters();
        String action = form.getFirst("action");
        CodeChallenge challenge = CodeChallenge.parse(session.getAuthNote(NOTE));
        long now = System.currentTimeMillis();
        UserModel existing = getExistingUser(context.getSession(), context.getRealm(), session);

        if ("send".equals(action) || "resend".equals(action)) {
            if (challenge != null && !challenge.canSendAnother()) {
                context.challenge(codePage(context, brokerContext, challenge, "linkCodeTooManyEmails"));
            } else if (challenge != null && !challenge.mayResend(now)) {
                context.challenge(codePage(context, brokerContext, challenge, "linkCodeWait"));
            } else {
                sendCode(context, brokerContext, existing, challenge, now);
            }
            return;
        }

        if ("verify".equals(action)) {
            if (challenge == null) {
                context.challenge(profilePage(context, brokerContext, null));
                return;
            }
            CodeChallenge.Check result = challenge.check(form.getFirst("code"), now);
            session.setAuthNote(NOTE, result.next().serialize());
            switch (result.outcome()) {
                case OK -> {
                    session.removeAuthNote(NOTE);
                    // They proved they own this mailbox, so the address is verified now.
                    existing.setEmailVerified(true);
                    context.setUser(existing);
                    context.getEvent().detail("link_verified_by", "email_code");
                    context.success();
                }
                case WRONG -> {
                    context.getEvent().user(existing).error(Errors.INVALID_USER_CREDENTIALS);
                    context.challenge(codePage(context, brokerContext, result.next(), "linkCodeWrong"));
                }
                case EXPIRED -> context.challenge(codePage(context, brokerContext, result.next(), "linkCodeExpired"));
                case LOCKED -> context.challenge(codePage(context, brokerContext, result.next(), "linkCodeLocked"));
            }
            return;
        }

        context.challenge(challenge == null
                ? profilePage(context, brokerContext, null)
                : codePage(context, brokerContext, challenge, null));
    }

    private void sendCode(
            AuthenticationFlowContext context,
            BrokeredIdentityContext brokerContext,
            UserModel existing,
            CodeChallenge previous,
            long now) {
        CodeChallenge.Issued issued = CodeChallenge.issue(previous, now, RANDOM);
        try {
            context.getSession()
                    .getProvider(EmailTemplateProvider.class)
                    .setRealm(context.getRealm())
                    .setUser(existing)
                    .send("linkCodeSubject", new ArrayList<>(), "link-code.ftl", emailAttributes(issued.code(), brokerContext));
        } catch (EmailException e) {
            LOG.error("Could not send the link code", e);
            context.challenge(profilePage(context, brokerContext, "linkCodeNotSent"));
            return;
        }
        context.getAuthenticationSession().setAuthNote(NOTE, issued.challenge().serialize());
        context.challenge(codePage(context, brokerContext, issued.challenge(), null));
    }

    /** A mutable map on purpose: Keycloak adds its own entries to it. */
    private static Map<String, Object> emailAttributes(String code, BrokeredIdentityContext brokerContext) {
        Map<String, Object> attributes = new HashMap<>();
        attributes.put("code", code);
        attributes.put("minutes", CodeChallenge.TTL_MS / 60000);
        attributes.put("provider", providerName(brokerContext));
        return attributes;
    }

    // --- pages ---------------------------------------------------------------------------------

    private Response profilePage(
            AuthenticationFlowContext context, BrokeredIdentityContext brokerContext, String errorKey) {
        LoginFormsProvider form = baseForm(context, brokerContext);
        if (errorKey != null) form.setError(errorKey);
        return form.createForm(PROFILE_PAGE);
    }

    private Response codePage(
            AuthenticationFlowContext context,
            BrokeredIdentityContext brokerContext,
            CodeChallenge challenge,
            String errorKey) {
        long now = System.currentTimeMillis();
        UserModel existing = getExistingUser(context.getSession(), context.getRealm(), context.getAuthenticationSession());
        LoginFormsProvider form = baseForm(context, brokerContext)
                .setAttribute("maskedEmail", mask(existing.getEmail()))
                .setAttribute("canResend", challenge.canSendAnother())
                .setAttribute("secondsUntilResend", challenge.secondsUntilResend(now))
                .setAttribute("attemptsLeft", challenge.attemptsLeft());
        if (errorKey != null) form.setError(errorKey);
        return form.createForm(CODE_PAGE);
    }

    private LoginFormsProvider baseForm(AuthenticationFlowContext context, BrokeredIdentityContext brokerContext) {
        ProfileInfo profile = ProfileInfo.from(brokerContext);
        UserModel existing = getExistingUser(context.getSession(), context.getRealm(), context.getAuthenticationSession());
        return context.form()
                .setExecution(context.getExecution().getId())
                .setAttribute("providerName", providerName(brokerContext))
                .setAttribute("profileName", profile.name())
                .setAttribute("profileEmail", profile.email())
                .setAttribute("profilePicture", profile.picture())
                .setAttribute("profileInitials", profile.initials())
                .setAttribute("accountEmail", mask(existing.getEmail()));
    }

    private static String providerName(BrokeredIdentityContext brokerContext) {
        String alias = brokerContext.getIdpConfig().getAlias();
        String display = brokerContext.getIdpConfig().getDisplayName();
        return display != null && !display.isBlank() ? display : alias;
    }

    /** j***@example.com: enough to recognise the address, not to learn it. */
    static String mask(String email) {
        if (email == null || !email.contains("@")) return "";
        int at = email.indexOf('@');
        return email.substring(0, Math.min(1, at)) + "***" + email.substring(at);
    }

    @Override
    public boolean requiresUser() {
        return false;
    }

    @Override
    public boolean configuredFor(
            org.keycloak.models.KeycloakSession session,
            org.keycloak.models.RealmModel realm,
            UserModel user) {
        return true;
    }

    @Override
    public void setRequiredActions(
            org.keycloak.models.KeycloakSession session,
            org.keycloak.models.RealmModel realm,
            UserModel user) {
        // nothing to set up
    }
}
