from django.db import models
from django.db.models import Q


class InboxConnection(models.Model):
    """Configuration/state placeholder for a mailbox provider. No tokens are stored here;
    real OAuth tokens must live in a secrets store once integration is implemented."""

    DEMO, GMAIL, MICROSOFT = "demo", "gmail", "microsoft"
    PROVIDERS = [(DEMO, "Demo (simulated inbox)"), (GMAIL, "Gmail API"), (MICROSOFT, "Microsoft Graph")]
    S_DEMO, S_DISCONNECTED, S_CONNECTED = "demo", "disconnected", "connected"
    STATES = [(S_DEMO, "Demo"), (S_DISCONNECTED, "Disconnected"), (S_CONNECTED, "Connected")]

    provider = models.CharField(max_length=12, choices=PROVIDERS, unique=True)
    state = models.CharField(max_length=14, choices=STATES, default=S_DISCONNECTED)
    account_email = models.EmailField(blank=True)
    folder = models.CharField(max_length=100, blank=True, default="INBOX")
    last_synced_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider}: {self.state}"


class InboxMessage(models.Model):
    NEW, SCANNED, VERIFIED, CONVERTED, DUPLICATE, REJECTED = "new", "scanned", "verified", "converted", "duplicate", "rejected"
    STATUS = [
        (NEW, "New"), (SCANNED, "Scanned"), (VERIFIED, "Verified"), (CONVERTED, "Converted to PO"),
        (DUPLICATE, "Duplicate"), (REJECTED, "Rejected"),
    ]

    provider = models.CharField(max_length=12, default="demo")
    external_id = models.CharField(max_length=200)  # mailbox message id; unique per provider
    sender_name = models.CharField(max_length=200, blank=True)
    sender_email = models.EmailField()
    subject = models.CharField(max_length=400)
    body = models.TextField(blank=True)
    received_at = models.DateTimeField()
    status = models.CharField(max_length=12, choices=STATUS, default=NEW)
    is_demo = models.BooleanField(default=False)
    converted_po = models.ForeignKey("purchase_orders.PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL, related_name="inbox_messages")
    status_note = models.CharField(max_length=300, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["provider", "external_id"], name="uniq_inbox_message_per_provider")]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["-received_at"]), models.Index(fields=["sender_email"])]

    def __str__(self):
        return f"{self.subject} <{self.sender_email}>"


class InboxAttachment(models.Model):
    message = models.ForeignKey(InboxMessage, on_delete=models.CASCADE, related_name="attachments")
    external_id = models.CharField(max_length=200)
    filename = models.CharField(max_length=300)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField(default=0)
    checksum = models.CharField(max_length=64, db_index=True)  # SHA-256 of content
    file = models.FileField(upload_to="inbox/")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["message", "external_id"], name="uniq_attachment_per_message")]

    def __str__(self):
        return self.filename
