from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.accounts.audit import log_action
from apps.accounts.exceptions import Conflict
from apps.accounts.permissions import user_role
from apps.ocr import services as ocr_services
from apps.ocr.serializers import OCRExtractionSerializer

from . import services
from .models import InboxAttachment, InboxConnection, InboxMessage
from .providers import ProviderNotConfigured
from .serializers import InboxConnectionSerializer, InboxMessageSerializer


def ensure_connections():
    defaults = {"demo": InboxConnection.S_DEMO, "gmail": InboxConnection.S_DISCONNECTED, "microsoft": InboxConnection.S_DISCONNECTED}
    for key, state in defaults.items():
        InboxConnection.objects.get_or_create(provider=key, defaults={"state": state})


class InboxMessageViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = InboxMessage.objects.prefetch_related("attachments__extractions").select_related("converted_po")
    serializer_class = InboxMessageSerializer
    filterset_fields = ["status", "provider", "is_demo"]
    search_fields = ["subject", "sender_name", "sender_email", "attachments__filename"]
    ordering_fields = ["received_at", "status", "sender_email"]

    @action(detail=False, methods=["post"])
    def sync(self, request):
        provider = request.data.get("provider", "demo")
        if provider == "demo" and settings.INBOX_MODE != "demo":
            raise ValidationError({"provider": "Demo inbox is disabled because INBOX_MODE is not 'demo'."})
        try:
            result = services.sync_inbox(provider)
        except ProviderNotConfigured as exc:
            raise Conflict(f"Cannot sync {provider}: {exc}")
        log_action(request.user, "sync", model_name="InboxMessage", details=result)
        return Response(result)

    @action(detail=False, methods=["post"])
    def simulate(self, request):
        if settings.INBOX_MODE != "demo":
            raise ValidationError({"detail": "Simulation is only available in demo mode."})
        msg = services.simulate_incoming()
        log_action(request.user, "simulate", msg)
        return Response(self.get_serializer(msg).data, status=201)

    @action(detail=True, methods=["post"])
    def scan(self, request, pk=None):
        msg = self.get_object()
        att = msg.attachments.first()
        if att is None:
            raise ValidationError({"detail": "This email has no attachment to scan."})
        if msg.status == InboxMessage.CONVERTED:
            raise Conflict("This email has already been converted to a purchase order.")
        if msg.status in (InboxMessage.DUPLICATE, InboxMessage.REJECTED):
            raise Conflict(f"This email is marked {msg.get_status_display()}; restore it before scanning.")
        ex = ocr_services.scan_attachment(att, request.user)
        log_action(request.user, "scan", ex)
        return Response(OCRExtractionSerializer(ex).data)

    @action(detail=True, methods=["post"])
    def mark(self, request, pk=None):
        msg = self.get_object()
        new = request.data.get("status")
        if new not in (InboxMessage.DUPLICATE, InboxMessage.REJECTED, "restore"):
            raise ValidationError({"status": "Use 'duplicate', 'rejected' or 'restore'."})
        if msg.status == InboxMessage.CONVERTED:
            raise Conflict("A converted email cannot be changed. Delete the PO first if it was created by mistake.")
        if new == "restore":
            has_scan = msg.attachments.filter(extractions__status__in=["processed", "verified"]).exists()
            msg.status = InboxMessage.SCANNED if has_scan else InboxMessage.NEW
            msg.status_note = ""
        else:
            msg.status = new
            msg.status_note = str(request.data.get("note", ""))[:300]
        msg.save(update_fields=["status", "status_note"])
        log_action(request.user, "update", msg, details={"status": msg.status})
        return Response(self.get_serializer(msg).data)


@api_view(["GET"])
def attachment_file(request, pk):
    att = get_object_or_404(InboxAttachment, pk=pk)
    return FileResponse(att.file.open("rb"), filename=att.filename, as_attachment=False, content_type=att.content_type)


class InboxConnectionViewSet(mixins.ListModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = InboxConnectionSerializer
    queryset = InboxConnection.objects.all().order_by("id")
    pagination_class = None
    http_method_names = ["get", "patch", "post", "head", "options"]

    def list(self, request, *args, **kwargs):
        ensure_connections()
        data = self.get_serializer(self.get_queryset(), many=True).data
        return Response({
            "mode": settings.INBOX_MODE,
            "mode_label": "Demo mode (simulated inbox)" if settings.INBOX_MODE == "demo" else "Live mode",
            "connections": data,
            "oauth_configured": {
                "gmail": bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET),
                "microsoft": bool(settings.MS_GRAPH_CLIENT_ID and settings.MS_GRAPH_CLIENT_SECRET and settings.MS_GRAPH_TENANT_ID),
            },
        })

    def partial_update(self, request, *args, **kwargs):
        if user_role(request.user) != "admin":
            return Response({"error": {"code": "permission_denied", "status": 403, "message": "Only Admin can change inbox configuration.", "details": {}}}, status=403)
        return super().partial_update(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def connect(self, request, pk=None):
        """Honest placeholder: the OAuth consent flow is not implemented, so this can never report 'connected'."""
        conn = self.get_object()
        if conn.provider == "demo":
            raise ValidationError({"detail": "The demo inbox is always available in demo mode; nothing to connect."})
        configured = (
            bool(settings.GMAIL_CLIENT_ID and settings.GMAIL_CLIENT_SECRET) if conn.provider == "gmail"
            else bool(settings.MS_GRAPH_CLIENT_ID and settings.MS_GRAPH_CLIENT_SECRET and settings.MS_GRAPH_TENANT_ID)
        )
        if not configured:
            raise Conflict(f"OAuth client credentials for {conn.get_provider_display()} are not configured in backend/.env.")
        raise Conflict(f"{conn.get_provider_display()} OAuth consent flow is not implemented yet; the mailbox remains disconnected.")
