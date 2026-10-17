"""The emails SELVIA sends. Each function returns a ready-to-send `Email`.

Kept short on purpose: one sentence, one button. Values are HTML-escaped; links are built by the
caller from the web app's address (see `frontend_url` in service.py).
"""

from html import escape

from app.services.email.senders import Email

# Email clients ignore stylesheets and theme tokens, so the colours are literal values that
# match the web app's neutral palette and blue accent.
_FONT = "-apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def _layout(
    heading: str, body: str, button_label: str | None = None, link: str | None = None
) -> str:
    button = ""
    fallback = ""
    if button_label and link:
        safe_link = escape(link, quote=True)
        button = (
            f'<p style="margin:24px 0 0"><a href="{safe_link}" style="background:#5146c7;'
            "color:#ffffff;text-decoration:none;padding:10px 18px;border-radius:6px;"
            f'font-weight:600;display:inline-block">{escape(button_label)}</a></p>'
        )
        fallback = (
            '<p style="margin:20px 0 0;font-size:12px;color:#6b7280">'
            f'Or open this link: <a href="{safe_link}" style="color:#6b7280">{safe_link}</a></p>'
        )
    return (
        f'<div style="background:#f4f4f5;padding:32px 16px;font-family:{_FONT}">'
        '<div style="max-width:480px;margin:0 auto;background:#ffffff;border:1px solid #e4e4e7;'
        'border-radius:8px;padding:28px">'
        '<p style="margin:0 0 20px;font-size:14px;font-weight:700;letter-spacing:0.08em;'
        'color:#18181b">SELVIA</p>'
        f'<h1 style="margin:0 0 12px;font-size:18px;color:#18181b">{escape(heading)}</h1>'
        f'<p style="margin:0;font-size:14px;line-height:1.6;color:#3f3f46">{body}</p>'
        f"{button}{fallback}</div>"
        '<p style="max-width:480px;margin:16px auto 0;font-size:12px;color:#a1a1aa">'
        "You received this because of activity on your SELVIA account.</p></div>"
    )


def team_invitation(
    to: str,
    *,
    inviter_name: str,
    team_name: str,
    as_lecturer: bool,
    link: str,
    expires_in_days: int,
) -> Email:
    role = "lecturer" if as_lecturer else "team member"
    subject = f"{inviter_name} invited you to {team_name}"
    text = (
        f"{inviter_name} invited you to join {team_name} on SELVIA as a {role}.\n\n"
        f"View the invitation: {link}\n\n"
        f"The link works for {expires_in_days} days."
    )
    body = (
        f"<strong>{escape(inviter_name)}</strong> invited you to join "
        f"<strong>{escape(team_name)}</strong> as a {role}. The link works for "
        f"{expires_in_days} days."
    )
    return Email(
        to,
        subject,
        text,
        _layout("You have a team invitation", body, "View invitation", link),
    )


def invitation_response(
    to: str, *, member_name: str, team_name: str, accepted: bool, link: str
) -> Email:
    verb = "accepted" if accepted else "declined"
    subject = f"{member_name} {verb} your invitation to {team_name}"
    text = (
        f"{member_name} {verb} your invitation to {team_name}.\n\nOpen SELVIA: {link}"
    )
    body = f"<strong>{escape(member_name)}</strong> {verb} your invitation to <strong>{escape(team_name)}</strong>."
    return Email(
        to, subject, text, _layout(f"Invitation {verb}", body, "Open SELVIA", link)
    )


def leader_transfer_request(
    to: str, *, from_name: str, team_name: str, link: str
) -> Email:
    subject = f"{from_name} asked you to lead {team_name}"
    text = (
        f"{from_name} asked you to take over as team leader of {team_name}.\n\n"
        f"Accept or decline in SELVIA: {link}"
    )
    body = (
        f"<strong>{escape(from_name)}</strong> asked you to take over as team leader of "
        f"<strong>{escape(team_name)}</strong>."
    )
    return Email(
        to, subject, text, _layout("Leadership request", body, "Review request", link)
    )


def leader_transfer_result(
    to: str, *, member_name: str, team_name: str, accepted: bool, link: str
) -> Email:
    if accepted:
        subject = f"{member_name} is now the leader of {team_name}"
        sentence = f"{member_name} accepted and is now the team leader of {team_name}."
        heading = "Leadership transferred"
    else:
        subject = f"{member_name} declined to lead {team_name}"
        sentence = f"{member_name} declined to take over as team leader of {team_name}. You are still the leader."
        heading = "Leadership request declined"
    return Email(
        to,
        subject,
        f"{sentence}\n\nOpen SELVIA: {link}",
        _layout(heading, escape(sentence), "Open SELVIA", link),
    )


def verification_code(to: str, *, code: str, purpose: str, minutes_valid: int) -> Email:
    subject = f"Your SELVIA code: {code}"
    text = f"Your code to {purpose} is {code}. It expires in {minutes_valid} minutes."
    body = (
        f"Use this code to {escape(purpose)}. It expires in {minutes_valid} minutes."
        f'<br><span style="display:inline-block;margin-top:16px;font-size:28px;font-weight:700;'
        f'letter-spacing:0.2em;color:#18181b">{escape(code)}</span>'
    )
    return Email(to, subject, text, _layout("Your verification code", body))
