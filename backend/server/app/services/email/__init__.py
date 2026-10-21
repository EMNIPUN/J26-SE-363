"""Email delivery: `get_email_service()` is the entry point; see service.py."""

from app.services.email.senders import (
    ConsoleEmailSender,
    Email,
    EmailError,
    EmailSender,
    InMemoryEmailSender,
    SmtpEmailSender,
)
from app.services.email.service import EmailService, generate_code, get_email_service

__all__ = [
    "ConsoleEmailSender",
    "Email",
    "EmailError",
    "EmailSender",
    "EmailService",
    "InMemoryEmailSender",
    "SmtpEmailSender",
    "generate_code",
    "get_email_service",
]
