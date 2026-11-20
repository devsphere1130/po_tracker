"""Mail provider interface. Implement fetch_new_messages() for a real mailbox.

DemoProvider  - works today; returns simulated emails (clearly flagged is_demo).
GmailProvider / MicrosoftGraphProvider - integration seams ONLY. They refuse to run until OAuth
credentials AND an authorised token exist. Nothing here claims a live mailbox connection.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from django.conf import settings

from . import demo_data


class ProviderError(Exception):
    pass


class ProviderNotConfigured(ProviderError):
    pass


@dataclass
class RawAttachment:
    external_id: str
    filename: str
    content_type: str
    content: bytes


@dataclass
class RawMessage:
    external_id: str
    sender_name: str
    sender_email: str
    subject: str
    body: str
    received_at: datetime
    attachments: List[RawAttachment] = field(default_factory=list)


class MailProvider(ABC):
    key = ""
    is_demo = False

    @abstractmethod
    def fetch_new_messages(self) -> List[RawMessage]:
        """Return messages not yet seen. De-duplication is enforced by the sync service."""


class DemoProvider(MailProvider):
    key = "demo"
    is_demo = True

    def fetch_new_messages(self):
        out = []
        for m in demo_data.build_demo_messages():
            out.append(RawMessage(
                external_id=m["external_id"], sender_name=m["sender_name"], sender_email=m["sender_email"],
                subject=m["subject"], body=m["body"], received_at=demo_data.received_at(m),
                attachments=[RawAttachment(**a) for a in m["attachments"]],
            ))
        return out


class GmailProvider(MailProvider):
    """Live Gmail (read-only OAuth). Works only after the user completed Google consent in Settings."""

    key = "gmail"
    MAX_NEW = 25
    MAX_PAGES = 4

    def fetch_new_messages(self):
        from . import gmail
        from .crypto import decrypt
        from .models import InboxConnection, InboxMessage

        conn = InboxConnection.objects.filter(provider="gmail").first()
        if not conn or conn.state != InboxConnection.S_CONNECTED or not conn.token_encrypted:
            raise ProviderNotConfigured("Gmail is not connected. Connect it in Settings > Inbox integration.")
        try:
            token = gmail.refresh_access_token(decrypt(conn.token_encrypted))
        except gmail.GmailAuthError:
            conn.state, conn.token_encrypted = InboxConnection.S_DISCONNECTED, ""
            conn.save(update_fields=["state", "token_encrypted", "updated_at"])
            raise ProviderNotConfigured("Google authorisation expired or was revoked. Reconnect Gmail in Settings.")
        except (gmail.GmailError, ValueError) as exc:
            raise ProviderError(str(exc))
        known = set(InboxMessage.objects.filter(provider="gmail").values_list("external_id", flat=True))
        out, page = [], None
        try:
            for _ in range(self.MAX_PAGES):
                ids, page = gmail.list_message_ids(token, page)
                for mid in ids:
                    if mid in known:
                        continue
                    data = gmail.parse_message(gmail.get_message(token, mid), token)
                    if not data["attachments"]:
                        continue  # no PDF/image attachment: not a PO document
                    out.append(RawMessage(
                        external_id=data["external_id"], sender_name=data["sender_name"], sender_email=data["sender_email"],
                        subject=data["subject"], body=data["body"], received_at=data["received_at"],
                        attachments=[RawAttachment(**a) for a in data["attachments"]],
                    ))
                    if len(out) >= self.MAX_NEW:
                        return out
                if not page:
                    break
        except gmail.GmailError as exc:
            raise ProviderError(str(exc))
        return out


class MicrosoftGraphProvider(MailProvider):
    """Future: Microsoft Graph. Steps: Azure app registration -> OAuth2 (Mail.Read) ->
    GET /me/mailFolders/inbox/messages?$filter=hasAttachments eq true&$expand=attachments.
    Message id = Graph message id (used for de-duplication)."""

    key = "microsoft"

    def fetch_new_messages(self):
        if not (settings.MS_GRAPH_CLIENT_ID and settings.MS_GRAPH_CLIENT_SECRET and settings.MS_GRAPH_TENANT_ID):
            raise ProviderNotConfigured("Microsoft Graph credentials are not set (MS_GRAPH_CLIENT_ID / _SECRET / _TENANT_ID).")
        raise ProviderNotConfigured("Microsoft Graph authorisation has not been completed; no mailbox is connected.")


PROVIDERS = {p.key: p for p in (DemoProvider, GmailProvider, MicrosoftGraphProvider)}


def get_provider(key):
    return PROVIDERS[key]()
