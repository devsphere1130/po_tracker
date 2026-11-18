from django.db.models import Count
from rest_framework import viewsets

from apps.accounts.audit import AuditMixin
from apps.accounts.exceptions import Conflict

from .models import Material, MaterialAlias
from .serializers import MaterialAliasSerializer, MaterialSerializer


class MaterialViewSet(AuditMixin, viewsets.ModelViewSet):
    serializer_class = MaterialSerializer
    search_fields = ["material_code", "name", "description", "category"]
    filterset_fields = ["is_active", "category", "uom"]
    ordering_fields = ["name", "material_code", "category", "default_rate", "created_at"]

    def get_queryset(self):
        return Material.objects.annotate(usage_count=Count("po_items")).order_by("name")

    def perform_destroy(self, instance):
        if instance.po_items.exists():
            raise Conflict(
                f"Cannot delete '{instance.name}': it is used in {instance.po_items.count()} PO line item(s). "
                "Deactivate the material instead."
            )
        super().perform_destroy(instance)


class MaterialAliasViewSet(AuditMixin, viewsets.ModelViewSet):
    queryset = MaterialAlias.objects.select_related("material")
    serializer_class = MaterialAliasSerializer
    search_fields = ["description", "material__name"]
    filterset_fields = ["material"]
