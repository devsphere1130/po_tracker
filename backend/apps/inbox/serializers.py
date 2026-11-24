from rest_framework import serializers

from .models import InboxAttachment, InboxConnection, InboxMessage


class InboxAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    extraction = serializers.SerializerMethodField()

    class Meta:
        model = InboxAttachment
        fields = ["id", "filename", "content_type", "size", "file_url", "extraction"]

    def get_file_url(self, obj):
        return f"/api/v1/inbox/attachments/{obj.pk}/file/"

    def get_extraction(self, obj):
        ex = obj.extractions.order_by("-id").first()
        if not ex:
            return None
        return {"id": ex.pk, "status": ex.status, "engine": ex.engine, "error_message": ex.error_message}


class InboxMessageSerializer(serializers.ModelSerializer):
    attachments = InboxAttachmentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    converted_po_number = serializers.CharField(source="converted_po.po_number", read_only=True, default=None)

    class Meta:
        model = InboxMessage
        fields = [
            "id", "provider", "sender_name", "sender_email", "subject", "body", "received_at", "status", "status_display",
            "status_note", "is_demo", "converted_po", "converted_po_number", "attachments", "imported_at",
        ]


class InboxConnectionSerializer(serializers.ModelSerializer):
    provider_display = serializers.CharField(source="get_provider_display", read_only=True)
    state_display = serializers.CharField(source="get_state_display", read_only=True)

    class Meta:
        model = InboxConnection
        fields = ["id", "provider", "provider_display", "state", "state_display", "account_email", "folder", "last_synced_at", "notes"]
        read_only_fields = ["provider", "state", "last_synced_at"]
