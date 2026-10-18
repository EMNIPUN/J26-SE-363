"""Ways to deliver an email: SMTP for real use, a logger for development, a list for tests."""

import logging
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage as MimeMessage
from email.utils import formataddr
from typing import Protocol

logger = logging.getLogger(__name__)

SMTP_TIMEOUT_SECONDS = 15


class EmailError(Exception):
    """The message could not be delivered."""


@dataclass(frozen=True)
class Email:
    to: str
    subject: str
    text: str
    html: str


class EmailSender(Protocol):
    def send(self, message: Email) -> None: ...


@dataclass
class SmtpEmailSender:
    host: str
    port: int
    from_address: str
    from_name: str
    username: str | None = None
    password: str | None = None
    security: str = "starttls"  # "starttls", "ssl" or "none"

    def send(self, message: Email) -> None:
        mime = MimeMessage()
        try:
            # EmailMessage rejects line breaks in headers, so a crafted name or subject cannot
            # inject extra headers.
            mime["From"] = formataddr((self.from_name, self.from_address))
            mime["To"] = message.to
            mime["Subject"] = message.subject
        except ValueError as exc:
            raise EmailError(
                f"Invalid email headers for {message.to!r}: {exc}"
            ) from exc
        mime.set_content(message.text)
        mime.add_alternative(message.html, subtype="html")

        try:
            with self._connect() as smtp:
                if self.security == "starttls":
                    smtp.starttls(context=ssl.create_default_context())
                if self.username:
                    smtp.login(self.username, self.password or "")
                smtp.send_message(mime)
        except (OSError, smtplib.SMTPException) as exc:
            raise EmailError(f"Could not send email to {message.to}: {exc}") from exc

    def _connect(self) -> smtplib.SMTP:
        if self.security == "ssl":
            return smtplib.SMTP_SSL(
                self.host,
                self.port,
                timeout=SMTP_TIMEOUT_SECONDS,
                context=ssl.create_default_context(),
            )
        return smtplib.SMTP(self.host, self.port, timeout=SMTP_TIMEOUT_SECONDS)


class ConsoleEmailSender:
    """Logs the message instead of sending it (development without an SMTP server)."""

    def send(self, message: Email) -> None:
        logger.info("Email to %s | %s\n%s", message.to, message.subject, message.text)


@dataclass
class InMemoryEmailSender:
    """Keeps sent messages in `outbox`, for tests."""

    outbox: list[Email] = field(default_factory=list)

    def send(self, message: Email) -> None:
        self.outbox.append(message)
