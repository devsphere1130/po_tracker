from rest_framework import serializers

from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem

from . import services
from .models import SupplyEntry


class SupplyEntrySerializer(serializers.ModelSerializer):
    po = serializers.PrimaryKeyRelatedField(queryset=PurchaseOrder.objects.all())
    item = serializers.PrimaryKeyRelatedField(queryset=PurchaseOrderItem.objects.all())
    po_number = serializers.CharField(source="po.po_number", read_only=True)
    customer_name = serializers.CharField(source="po.customer.name", read_only=True)
    material_name = serializers.CharField(source="item.material.name", read_only=True)
    uom = serializers.CharField(source="item.uom", read_only=True)
    item_pending_quantity = serializers.DecimalField(source="item.pending_quantity", max_digits=14, decimal_places=3, read_only=True)
    po_status = serializers.CharField(source="po.status", read_only=True)

    class Meta:
        model = SupplyEntry
        fields = [
            "id", "po", "po_number", "customer_name", "item", "material_name", "uom", "supply_date", "quantity",
            "challan_number", "remarks", "item_pending_quantity", "po_status", "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_quantity(self, v):
        if v <= 0:
            raise serializers.ValidationError("Supplied quantity must be greater than zero.")
        return v

    def validate(self, attrs):
        po = attrs.get("po") or (self.instance.po if self.instance else None)
        item = attrs.get("item") or (self.instance.item if self.instance else None)
        if self.instance and "po" in attrs and attrs["po"].pk != self.instance.po_id:
            raise serializers.ValidationError({"po": "A supply entry cannot be moved to another PO."})
        if po and item and item.po_id != po.pk:
            raise serializers.ValidationError({"item": "Line item does not belong to the selected PO."})
        return attrs

    def create(self, v):
        return services.record_supply(
            v["po"], v["item"], v["supply_date"], v["quantity"], v.get("challan_number", ""), v.get("remarks", ""),
            self.context["request"].user,
        )

    def update(self, instance, v):
        v.pop("po", None)
        return services.update_supply(instance, v)
