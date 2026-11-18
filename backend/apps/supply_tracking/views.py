import django_filters
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.accounts.audit import log_action

from . import services
from .models import SupplyEntry
from .serializers import SupplyEntrySerializer


class SupplyEntryFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="supply_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="supply_date", lookup_expr="lte")
    customer = django_filters.NumberFilter(field_name="po__customer")
    material = django_filters.NumberFilter(field_name="item__material")

    class Meta:
        model = SupplyEntry
        fields = ["po", "item"]


class SupplyEntryViewSet(viewsets.ModelViewSet):
    """Supply entries. Create/update/delete go through transaction-safe services."""

    serializer_class = SupplyEntrySerializer
    filterset_class = SupplyEntryFilter
    search_fields = ["po__po_number", "po__customer__name", "challan_number", "item__material__name", "remarks"]
    ordering_fields = ["supply_date", "quantity", "created_at"]

    def get_queryset(self):
        return SupplyEntry.objects.select_related("po__customer", "item__material")

    def perform_create(self, serializer):
        log_action(self.request.user, "create", serializer.save())

    def perform_update(self, serializer):
        log_action(self.request.user, "update", serializer.save())

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        log_action(request.user, "delete", entry)
        services.delete_supply(entry)
        return Response(status=status.HTTP_204_NO_CONTENT)
