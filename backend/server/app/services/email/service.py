"""Sends the application's emails without ever failing the request that triggered them."""

import logging
import secrets
from urllib.parse import urlsplit

from fastapi import Request

from app.core.config import settings
from app.services.email import templates
from app.services.email.senders import (
    ConsoleEmailSender,
    Email,
    EmailError,
    EmailSender,
    SmtpEmailSender,
)

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, sender: EmailSender, base_url: str):
        self._sender = sender
        self._base_url = base_url.rstrip("/")

    # --- delivery ---------------------------------------------------------------------------

    def deliver(self, message: Email) -> None:
        """Send one message. Meant for FastAPI background tasks: errors are logged, not raised,
        because the action that caused the email has already succeeded."""
        try:
            self._sender.send(message)
        except EmailError:
            logger.exception("Email delivery failed")
        except Exception:  # a sender bug must not crash the worker thread
            logger.exception("Unexpected error while sending an email")

    # --- messages ---------------------------------------------------------------------------

    def team_invitation(
        self,
        to: str,
        *,
        inviter_name: str,
        team_name: str,
        as_lecturer: bool,
        token: str,
        expires_in_days: int,
    ) -> Email:
        return templates.team_invitation(
            to,
            inviter_name=inviter_name,
            team_name=team_name,
            as_lecturer=as_lecturer,
            link=f"{self._base_url}/invitations?token={token}",
            expires_in_days=expires_in_days,
        )

    # `path` is where in the web app the button leads, e.g. /teams/J26-SE-363/members.

    def invitation_response(
        self,
        to: str,
        *,
        member_name: str,
        team_name: str,
        accepted: bool,
        path: str = "/home",
    ) -> Email:
        return templates.invitation_response(
            to,
            member_name=member_name,
            team_name=team_name,
            accepted=accepted,
            link=f"{self._base_url}{path}",
        )

    def leader_transfer_request(
        self, to: str, *, from_name: str, team_name: str, path: str = "/home"
    ) -> Email:
        return templates.leader_transfer_request(
            to,
            from_name=from_name,
            team_name=team_name,
            link=f"{self._base_url}{path}",
        )

    def leader_transfer_result(
        self,
        to: str,
        *,
        member_name: str,
        team_name: str,
        accepted: bool,
        path: str = "/home",
    ) -> Email:
        return templates.leader_transfer_result(
            to,
            member_name=member_name,
            team_name=team_name,
            accepted=accepted,
            link=f"{self._base_url}{path}",
        )

    def notice(
        self, to: str, *, subject: str, heading: str, sentence: str, path: str = "/home"
    ) -> Email:
        return templates.notice(
            to,
            subject=subject,
            heading=heading,
            sentence=sentence,
            link=f"{self._base_url}{path}",
        )

    def verification_code(
        self, to: str, *, code: str, purpose: str, minutes_valid: int
    ) -> Email:
        return templates.verification_code(
            to, code=code, purpose=purpose, minutes_valid=minutes_valid
        )


def generate_code(length: int = 6) -> str:
    """A random numeric one-time code, for `verification_code` emails."""
    return "".join(secrets.choice("0123456789") for _ in range(length))


def build_sender() -> EmailSender:
    if settings.EMAIL_BACKEND == "smtp":
        return SmtpEmailSender(
            host=settings.SMTP_HOST or "",
            port=settings.SMTP_PORT,
            from_address=settings.EMAIL_FROM_ADDRESS,
            from_name=settings.EMAIL_FROM_NAME,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
            security=settings.SMTP_SECURITY,
        )
    return ConsoleEmailSender()


def _origin_of(url: str | None) -> str | None:
    parts = urlsplit(url or "")
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else None


def frontend_url(request: Request) -> str:
    """The web app the person is using, so a link in an email opens the same one: localhost while
    developing, the Vercel address once deployed.

    It is taken from the browser's Origin (or Referer) header, but only if it is one of the
    configured web apps (CORS_ORIGINS or APP_BASE_URL). Anything else, including a header made up
    by someone, falls back to APP_BASE_URL, so an email can never be made to link to another site.
    """
    allowed = {origin.rstrip("/") for origin in settings.CORS_ORIGINS}
    allowed.add(settings.APP_BASE_URL.rstrip("/"))
    asked = request.headers.get("origin") or _origin_of(request.headers.get("referer"))
    if asked and asked.rstrip("/") in allowed:
        return asked.rstrip("/")
    return settings.APP_BASE_URL.rstrip("/")


def get_email_service(request: Request) -> EmailService:
    """FastAPI dependency. Tests replace it with `app.dependency_overrides`."""
    return EmailService(build_sender(), frontend_url(request))
