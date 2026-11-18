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


class ProviderNotConfigured(Exception):
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
    """Future: Gmail API. Steps: OAuth2 consent (scope gmail.readonly) -> store refresh token securely ->
    users.messages.list(q='has:attachment label:inbox') -> users.messages.get(format='full') ->
    users.messages.attachments.get. Message id = Gmail message id (stable, used for de-duplication)."""

    key = "gmail"

    def fetch_new_messages(self):
        if not (settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET):
            raise ProviderNotConfigured("Gmail OAuth client credentials are not set (GMAIL_CLIENT_ID / GMAIL_CLIENT_SECRET).")
        raise ProviderNotConfigured("Gmail OAuth authorisation has not been completed; no mailbox is connected.")


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
