from django.conf import settings
from django.db import models


class OCRExtraction(models.Model):
    PENDING, PROCESSED, FAILED, VERIFIED, CONVERTED = "pending", "processed", "failed", "verified", "converted"
    STATUS = [(PENDING, "Pending"), (PROCESSED, "Processed"), (FAILED, "Failed"), (VERIFIED, "Verified"), (CONVERTED, "Converted to PO")]

    attachment = models.ForeignKey("inbox.InboxAttachment", null=True, blank=True, on_delete=models.SET_NULL, related_name="extractions")
    file = models.FileField(upload_to="ocr_uploads/", null=True, blank=True)  # direct uploads only
    original_filename = models.CharField(max_length=300)
    content_type = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=10, choices=STATUS, default=PENDING)
    engine = models.CharField(max_length=30, blank=True)  # pdf-text | tesseract
    ocr_confidence = models.FloatField(null=True, blank=True)
    raw_text = models.TextField(blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)  # machine output (never edited)
    draft_data = models.JSONField(default=dict, blank=True)  # user's in-progress corrections
    verified_data = models.JSONField(default=dict, blank=True)  # final, user-verified form
    error_message = models.TextField(blank=True)
    linked_po = models.ForeignKey("purchase_orders.PurchaseOrder", null=True, blank=True, on_delete=models.SET_NULL, related_name="ocr_extractions")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self):
        return f"OCR #{self.pk} {self.original_filename} [{self.status}]"

    @property
    def source_file(self):
        return self.attachment.file if self.attachment_id else self.file
