import django_filters
from django.db.models import Q
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.audit import log_action

from . import services
from .models import PurchaseOrder
from .serializers import CancelSerializer, PurchaseOrderListSerializer, PurchaseOrderSerializer

ALLOWED_ATTACHMENT_EXT = (".pdf", ".png", ".jpg", ".jpeg")


class PurchaseOrderFilter(django_filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=PurchaseOrder.STATUS_CHOICES)
    po_date_from = django_filters.DateFilter(field_name="po_date", lookup_expr="gte")
    po_date_to = django_filters.DateFilter(field_name="po_date", lookup_expr="lte")
    delivery_from = django_filters.DateFilter(field_name="delivery_date", lookup_expr="gte")
    delivery_to = django_filters.DateFilter(field_name="delivery_date", lookup_expr="lte")
    material = django_filters.NumberFilter(field_name="items__material", distinct=True)
    overdue = django_filters.BooleanFilter(method="filter_overdue")

    class Meta:
        model = PurchaseOrder
        fields = ["customer", "source"]

    def filter_overdue(self, qs, name, value):
        cond = Q(delivery_date__lt=timezone.localdate(), status__in=["pending", "partial"])
        return qs.filter(cond) if value else qs.exclude(cond)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    filterset_class = PurchaseOrderFilter
    search_fields = ["po_number", "customer__name", "customer__customer_code", "notes", "items__original_description", "items__material__name"]
    ordering_fields = ["po_date", "delivery_date", "order_total", "po_number", "created_at", "status"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related("customer").prefetch_related("items__material")
        return qs.distinct()

    def get_serializer_class(self):
        return PurchaseOrderListSerializer if self.action == "list" else PurchaseOrderSerializer

    def perform_create(self, serializer):
        po = serializer.save()
        log_action(self.request.user, "create", po)

    def perform_update(self, serializer):
        po = serializer.save()
        log_action(self.request.user, "update", po)

    def destroy(self, request, *args, **kwargs):
        po = self.get_object()
        log_action(request.user, "delete", po)
        services.delete_purchase_order(po)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        ser = CancelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        po = services.cancel_purchase_order(self.get_object(), ser.validated_data.get("reason", ""))
        log_action(request.user, "cancel", po, details=ser.validated_data)
        return Response(PurchaseOrderSerializer(self.get_queryset().get(pk=po.pk)).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        po = services.reopen_purchase_order(self.get_object())
        log_action(request.user, "reopen", po)
        return Response(PurchaseOrderSerializer(self.get_queryset().get(pk=po.pk)).data)

    @action(detail=True, methods=["get", "post"], url_path="attachment")
    def attachment(self, request, pk=None):
        po = self.get_object()
        if request.method == "POST":
            f = request.FILES.get("file")
            if not f or not f.name.lower().endswith(ALLOWED_ATTACHMENT_EXT):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"file": "Upload a PDF, PNG or JPG file."})
            po.attachment.save(f.name, f, save=True)
            log_action(request.user, "update", po, details={"attachment": f.name})
            return Response(PurchaseOrderSerializer(self.get_queryset().get(pk=po.pk)).data)
        if not po.attachment:
            raise Http404("No attachment")
        return FileResponse(po.attachment.open("rb"), as_attachment=False, filename=po.attachment.name.split("/")[-1])
