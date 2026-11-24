from django.conf import settings
from django.http import FileResponse
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.audit import log_action
from apps.accounts.exceptions import Conflict
from apps.purchase_orders.serializers import PurchaseOrderSerializer

from . import services
from .extractor import SUPPORTED_EXT, tesseract_info
from .models import OCRExtraction
from .serializers import OCRExtractionSerializer


class OCRExtractionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    queryset = OCRExtraction.objects.select_related("attachment__message", "linked_po")
    serializer_class = OCRExtractionSerializer
    filterset_fields = ["status", "engine"]
    search_fields = ["original_filename", "raw_text"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_update(self, serializer):
        ex = serializer.instance
        if ex.status in (OCRExtraction.CONVERTED,):
            raise Conflict("Already converted; it can no longer be edited.")
        serializer.save()
        if ex.status == OCRExtraction.VERIFIED:  # editing after verification requires re-verifying
            ex.status = OCRExtraction.PROCESSED
            ex.verified_data = {}
            ex.save(update_fields=["status", "verified_data"])

    @action(detail=False, methods=["post"])
    def upload(self, request):
        f = request.FILES.get("file")
        if not f:
            raise ValidationError({"file": "No file uploaded."})
        ext = "." + f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext not in SUPPORTED_EXT:
            raise ValidationError({"file": "Unsupported file type. Upload a PDF, PNG, JPG or JPEG."})
        if f.size > settings.MAX_UPLOAD_BYTES:
            raise ValidationError({"file": "File is too large (max 10 MB)."})
        ex = OCRExtraction.objects.create(
            file=f, original_filename=f.name, content_type=f.content_type or "", created_by=request.user
        )
        services.run_extraction(ex)
        log_action(request.user, "create", ex)
        return Response(self.get_serializer(ex).data, status=201)

    @action(detail=True, methods=["post"])
    def scan(self, request, pk=None):
        ex = services.run_extraction(self.get_object())
        log_action(request.user, "scan", ex)
        return Response(self.get_serializer(ex).data)

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        ex = services.verify_extraction(self.get_object(), request.data, request.user)
        log_action(request.user, "verify", ex)
        return Response(self.get_serializer(ex).data)

    @action(detail=True, methods=["post"], url_path="create-po")
    def create_po(self, request, pk=None):
        po = services.create_po_from_extraction(self.get_object(), request.user, save_aliases=request.data.get("save_aliases", True))
        log_action(request.user, "create", po, details={"from_ocr": pk})
        return Response(PurchaseOrderSerializer(po).data, status=201)

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        ex = self.get_object()
        f = ex.source_file
        return FileResponse(f.open("rb"), filename=ex.original_filename, as_attachment=False)

    @action(detail=False, methods=["get"], url_path="engine-status")
    def engine_status(self, request):
        return Response(tesseract_info())
