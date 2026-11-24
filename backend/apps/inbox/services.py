import hashlib

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import InboxAttachment, InboxConnection, InboxMessage
from .providers import get_provider


def import_message(raw, provider_key, is_demo=False):
    """Store one raw message. Returns (message, created). Never imports the same mailbox message or
    attachment twice. An attachment whose content was already imported under another message flags
    the new message as a probable duplicate."""
    existing = InboxMessage.objects.filter(provider=provider_key, external_id=raw.external_id).first()
    if existing:
        return existing, False
    try:
        with transaction.atomic():
            msg = InboxMessage.objects.create(
                provider=provider_key, external_id=raw.external_id, sender_name=raw.sender_name,
                sender_email=raw.sender_email, subject=raw.subject, body=raw.body,
                received_at=raw.received_at, is_demo=is_demo,
            )
            dup_of = None
            for att in raw.attachments:
                checksum = hashlib.sha256(att.content).hexdigest()
                prior = InboxAttachment.objects.filter(checksum=checksum).exclude(message=msg).select_related("message").first()
                if prior and prior.message.status != InboxMessage.REJECTED:
                    dup_of = prior.message
                obj = InboxAttachment(
                    message=msg, external_id=att.external_id, filename=att.filename,
                    content_type=att.content_type, size=len(att.content), checksum=checksum,
                )
                obj.file.save(f"{checksum[:12]}_{att.filename}", ContentFile(att.content), save=False)
                obj.save()
            if dup_of:
                msg.status = InboxMessage.DUPLICATE
                msg.status_note = f"Same attachment already received in message #{dup_of.pk}."
                msg.save(update_fields=["status", "status_note"])
    except IntegrityError:  # concurrent sync imported it first
        return InboxMessage.objects.get(provider=provider_key, external_id=raw.external_id), False
    return msg, True


def sync_inbox(provider_key="demo"):
    provider = get_provider(provider_key)
    messages = provider.fetch_new_messages()  # raises ProviderNotConfigured for unconfigured live providers
    created = skipped = 0
    for raw in messages:
        _, was_created = import_message(raw, provider.key, is_demo=provider.is_demo)
        created += was_created
        skipped += not was_created
    conn, _ = InboxConnection.objects.get_or_create(provider=provider_key)
    conn.last_synced_at = timezone.now()
    conn.save(update_fields=["last_synced_at", "updated_at"])
    return {"imported": created, "already_imported": skipped, "demo": provider.is_demo}


def simulate_incoming():
    """Demo only: create a brand-new simulated PO email."""
    from . import demo_data
    from .providers import RawAttachment, RawMessage

    seq = InboxMessage.objects.filter(external_id__startswith="demo-gen-").count() + 1
    m = demo_data.build_generated_message(seq)
    raw = RawMessage(
        external_id=m["external_id"], sender_name=m["sender_name"], sender_email=m["sender_email"], subject=m["subject"],
        body=m["body"], received_at=m["received_at"], attachments=[RawAttachment(**a) for a in m["attachments"]],
    )
    return import_message(raw, "demo", is_demo=True)[0]
