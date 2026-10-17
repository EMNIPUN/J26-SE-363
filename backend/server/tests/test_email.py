import logging
import smtplib
from typing import ClassVar

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.services.email import (
    ConsoleEmailSender,
    Email,
    EmailError,
    EmailService,
    InMemoryEmailSender,
    SmtpEmailSender,
    generate_code,
    templates,
)

BASE_URL = "https://selvia.example/"
MESSAGE = Email("ada@example.com", "Hello", "plain body", "<p>html body</p>")


# --- templates -------------------------------------------------------------------------------


def test_invitation_email_has_the_link_the_team_and_the_expiry():
    email = EmailService(InMemoryEmailSender(), BASE_URL).team_invitation(
        "sam@example.com",
        inviter_name="Dr. Ada Perera",
        team_name="Team Alpha",
        as_lecturer=False,
        token="abc123",
        expires_in_days=14,
    )

    assert email.to == "sam@example.com"
    assert email.subject == "Dr. Ada Perera invited you to Team Alpha"
    link = "https://selvia.example/invitations?token=abc123"  # no double slash from the base URL
    assert link in email.text and link in email.html
    assert "team member" in email.text
    assert "14 days" in email.text


def test_invitation_email_names_the_lecturer_role():
    email = EmailService(InMemoryEmailSender(), BASE_URL).team_invitation(
        "x@example.com",
        inviter_name="A",
        team_name="T",
        as_lecturer=True,
        token="t",
        expires_in_days=1,
    )

    assert "lecturer" in email.text


def test_names_are_escaped_in_html_but_not_in_plain_text():
    email = templates.team_invitation(
        "x@example.com",
        inviter_name='<script>alert("x")</script>',
        team_name="R&D",
        as_lecturer=False,
        link="https://selvia.example/invitations?token=a&b=c",
        expires_in_days=3,
    )

    assert "<script>" not in email.html
    assert "&lt;script&gt;" in email.html
    assert "R&amp;D" in email.html
    assert "token=a&amp;b=c" in email.html  # inside an href attribute
    assert "R&D" in email.text


@pytest.mark.parametrize("accepted", [True, False])
def test_invitation_response_says_what_happened(accepted):
    email = templates.invitation_response(
        "ada@example.com",
        member_name="Sam",
        team_name="Alpha",
        accepted=accepted,
        link="https://x",
    )

    assert ("accepted" if accepted else "declined") in email.subject


def test_leader_transfer_emails():
    request = templates.leader_transfer_request(
        "sam@example.com", from_name="Kim", team_name="Alpha", link="https://x"
    )
    accepted = templates.leader_transfer_result(
        "kim@example.com",
        member_name="Sam",
        team_name="Alpha",
        accepted=True,
        link="https://x",
    )
    declined = templates.leader_transfer_result(
        "kim@example.com",
        member_name="Sam",
        team_name="Alpha",
        accepted=False,
        link="https://x",
    )

    assert "asked you to lead Alpha" in request.subject
    assert "is now the leader" in accepted.subject
    assert "declined" in declined.subject and "still the leader" in declined.text


def test_verification_code_email_and_generator():
    email = templates.verification_code(
        "x@example.com", code="123456", purpose="confirm your email", minutes_valid=10
    )
    code = generate_code()

    assert "123456" in email.subject and "123456" in email.html
    assert "10 minutes" in email.text
    assert len(code) == 6 and code.isdigit()
    assert len({generate_code() for _ in range(20)}) > 1


# --- delivery --------------------------------------------------------------------------------


class FakeSmtp:
    instances: ClassVar[list["FakeSmtp"]] = []

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port, self.context = host, port, context
        self.calls: list[tuple] = []
        FakeSmtp.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.calls.append(("starttls",))

    def login(self, username, password):
        self.calls.append(("login", username, password))

    def send_message(self, mime):
        self.calls.append(("send", mime))


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSmtp.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSmtp)
    return FakeSmtp


def smtp_sender(**overrides) -> SmtpEmailSender:
    options = {
        "host": "smtp.example.com",
        "port": 587,
        "from_address": "no-reply@selvia.example",
        "from_name": "SELVIA",
        **overrides,
    }
    return SmtpEmailSender(**options)


def test_smtp_sender_uses_starttls_logs_in_and_sends_html_and_text(fake_smtp):
    smtp_sender(username="user", password="secret").send(MESSAGE)

    (smtp,) = fake_smtp.instances
    assert smtp.calls[:2] == [("starttls",), ("login", "user", "secret")]
    mime = smtp.calls[2][1]
    assert mime["To"] == "ada@example.com"
    assert mime["Subject"] == "Hello"
    assert "SELVIA" in mime["From"] and "no-reply@selvia.example" in mime["From"]
    assert (
        mime.get_body(preferencelist=("plain",)).get_content().strip() == "plain body"
    )
    assert "html body" in mime.get_body(preferencelist=("html",)).get_content()


def test_smtp_sender_without_credentials_or_tls(fake_smtp):
    smtp_sender(security="none", port=1025).send(MESSAGE)

    (smtp,) = fake_smtp.instances
    assert [call[0] for call in smtp.calls] == ["send"]
    assert smtp.port == 1025


def test_smtp_sender_ssl_skips_starttls(fake_smtp):
    smtp_sender(security="ssl", port=465, username="u", password="p").send(MESSAGE)

    (smtp,) = fake_smtp.instances
    assert [call[0] for call in smtp.calls] == ["login", "send"]
    assert smtp.context is not None


def test_smtp_failures_become_email_errors(monkeypatch):
    def refuse(*args, **kwargs):
        raise ConnectionRefusedError("nobody is listening")

    monkeypatch.setattr(smtplib, "SMTP", refuse)

    with pytest.raises(EmailError, match="ada@example.com"):
        smtp_sender().send(MESSAGE)


def test_header_injection_is_rejected_before_connecting(fake_smtp):
    evil = Email("ada@example.com", "Hi\r\nBcc: attacker@example.com", "t", "<p>h</p>")

    with pytest.raises(EmailError, match="Invalid email headers"):
        smtp_sender().send(evil)

    assert fake_smtp.instances == []


def test_deliver_never_raises(caplog):
    class Broken:
        def send(self, message):
            raise EmailError("provider is down")

    class Buggy:
        def send(self, message):
            raise RuntimeError("bug")

    for sender in (Broken(), Buggy()):
        with caplog.at_level(logging.ERROR):
            EmailService(sender, BASE_URL).deliver(MESSAGE)

    assert len([r for r in caplog.records if r.levelno == logging.ERROR]) == 2


def test_deliver_hands_the_message_to_the_sender():
    sender = InMemoryEmailSender()

    EmailService(sender, BASE_URL).deliver(MESSAGE)

    assert sender.outbox == [MESSAGE]


def test_console_sender_logs_instead_of_sending(caplog):
    with caplog.at_level(logging.INFO):
        ConsoleEmailSender().send(MESSAGE)

    assert "ada@example.com" in caplog.text and "plain body" in caplog.text


# --- settings --------------------------------------------------------------------------------


def test_smtp_backend_requires_a_host():
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        Settings(EMAIL_BACKEND="smtp", SMTP_HOST=None, _env_file=None)


def test_console_backend_is_the_default(monkeypatch):
    # A developer's own .env may switch on real mail; the default is what counts here.
    monkeypatch.delenv("EMAIL_BACKEND", raising=False)
    assert Settings(_env_file=None).EMAIL_BACKEND == "console"
