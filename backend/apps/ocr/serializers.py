from rest_framework import serializers

from .models import OCRExtraction


class OCRExtractionSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    linked_po_number = serializers.CharField(source="linked_po.po_number", read_only=True, default=None)
    message_id = serializers.SerializerMethodField()
    is_demo = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    working_data = serializers.SerializerMethodField()
    low_confidence = serializers.SerializerMethodField()

    class Meta:
        model = OCRExtraction
        fields = [
            "id", "attachment", "message_id", "original_filename", "content_type", "status", "status_display", "engine",
            "ocr_confidence", "raw_text", "extracted_data", "draft_data", "verified_data", "working_data", "error_message",
            "linked_po", "linked_po_number", "file_url", "is_demo", "low_confidence", "verified_at", "created_at",
        ]
        read_only_fields = [f for f in fields if f != "draft_data"]

    def get_file_url(self, obj):
        return f"/api/v1/ocr/extractions/{obj.pk}/file/"

    def get_message_id(self, obj):
        return obj.attachment.message_id if obj.attachment_id else None

    def get_is_demo(self, obj):
        return bool(obj.attachment_id and obj.attachment.message.is_demo)

    def get_working_data(self, obj):
        return obj.verified_data or obj.draft_data or (obj.extracted_data or {}).get("form") or {}

    def get_low_confidence(self, obj):
        d = obj.extracted_data or {}
        if not d:
            return False
        hdr_bad = any(f["status"] != "ok" for f in d.get("header", {}).values())
        item_bad = any(i["confidence"] < 0.8 or i["flags"] for i in d.get("items", []))
        return hdr_bad or item_bad
