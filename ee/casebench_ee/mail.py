# SPDX-License-Identifier: Elastic-2.0
"""Sign-in links by email, through the SMTP server the deployment names (decision 0058)."""

import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol


class Mailer(Protocol):
    """Sends one email; False when this server sends no email, so the admin passes it on."""

    def send(self, to: str, subject: str, text: str) -> bool: ...


class NoMail:
    """No SMTP is configured."""

    def send(self, to: str, subject: str, text: str) -> bool:
        return False


@dataclass
class Smtp:
    """`security` is starttls on port 587, tls on port 465, or none on a trusted network."""

    host: str
    port: int
    sender: str
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    security: str = "starttls"

    def send(self, to: str, subject: str, text: str) -> bool:
        message = EmailMessage()
        message["From"], message["To"], message["Subject"] = self.sender, to, subject
        message.set_content(text)
        context = ssl.create_default_context()
        if self.security == "tls":
            server: smtplib.SMTP = smtplib.SMTP_SSL(self.host, self.port, context=context)
        else:
            server = smtplib.SMTP(self.host, self.port)
        with server:
            if self.security == "starttls":
                server.starttls(context=context)
            if self.username:
                server.login(self.username, self.password or "")
            server.send_message(message)
        return True


@dataclass
class Outbox:
    """Keeps what would be sent, for tests."""

    sent: list[tuple[str, str, str]] = field(default_factory=list)

    def send(self, to: str, subject: str, text: str) -> bool:
        self.sent.append((to, subject, text))
        return True
