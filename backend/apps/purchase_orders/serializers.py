from decimal import Decimal

from rest_framework import serializers

from apps.customers.models import Customer
from apps.materials.models import Material

from . import services
from .models import PurchaseOrder, PurchaseOrderItem


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    material_name = serializers.CharField(source="material.name", read_only=True)
    material_code = serializers.CharField(source="material.material_code", read_only=True)
    pending_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    progress_percent = serializers.FloatField(read_only=True)
    line_amount = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)
    supplied_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id", "material", "material_name", "material_code", "original_description", "ordered_quantity", "uom",
            "unit_price", "line_amount", "supplied_quantity", "pending_quantity", "progress_percent",
        ]

    def validate_ordered_quantity(self, v):
        if v <= 0:
            raise serializers.ValidationError("Ordered quantity must be greater than zero.")
        return v

    def validate_unit_price(self, v):
        if v < 0:
            raise serializers.ValidationError("Unit price cannot be negative.")
        return v


class SupplyHistorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    item = serializers.IntegerField(source="item_id")
    material_name = serializers.CharField(source="item.material.name")
    supply_date = serializers.DateField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3)
    uom = serializers.CharField(source="item.uom")
    challan_number = serializers.CharField()
    remarks = serializers.CharField()


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    item_count = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "po_number", "customer", "customer_name", "po_date", "delivery_date", "source", "status",
            "status_display", "order_total", "is_overdue", "item_count", "progress_percent", "created_at",
        ]

    def get_item_count(self, obj):
        return len(obj.items.all())

    def get_progress_percent(self, obj):
        # mean of per-line fulfilment (unit-independent; derived from quantities)
        items = list(obj.items.all())
        if not items:
            return 0.0
        return round(sum(i.progress_percent for i in items) / len(items), 1)


class PurchaseOrderSerializer(PurchaseOrderListSerializer):
    items = PurchaseOrderItemSerializer(many=True)
    supply_entries = serializers.SerializerMethodField()
    attachment_url = serializers.SerializerMethodField()
    attachment_name = serializers.SerializerMethodField()
    customer_detail = serializers.SerializerMethodField()

    class Meta(PurchaseOrderListSerializer.Meta):
        fields = PurchaseOrderListSerializer.Meta.fields + [
            "notes", "items", "supply_entries", "attachment_url", "attachment_name", "cancel_reason",
            "cancelled_at", "customer_detail", "updated_at",
        ]
        read_only_fields = ["status", "order_total", "cancel_reason", "cancelled_at"]

    def get_supply_entries(self, obj):
        entries = obj.supply_entries.select_related("item__material").order_by("-supply_date", "-id")
        return SupplyHistorySerializer(entries, many=True).data

    def get_attachment_url(self, obj):
        return f"/api/v1/purchase-orders/{obj.pk}/attachment/" if obj.attachment else None

    def get_attachment_name(self, obj):
        return obj.attachment.name.split("/")[-1] if obj.attachment else None

    def get_customer_detail(self, obj):
        c = obj.customer
        return {"id": c.id, "name": c.name, "customer_code": c.customer_code, "email": c.email, "mobile": c.mobile,
                "gst_number": c.gst_number, "billing_address": c.billing_address, "shipping_address": c.shipping_address}

    def validate_po_number(self, v):
        v = v.strip()
        if not v:
            raise serializers.ValidationError("PO number is required.")
        return v

    def validate_customer(self, c):
        if not c.is_active and (self.instance is None or self.instance.customer_id != c.pk):
            raise serializers.ValidationError("Customer is inactive.")
        return c

    def validate(self, attrs):
        po_date = attrs.get("po_date", getattr(self.instance, "po_date", None))
        delivery = attrs.get("delivery_date", getattr(self.instance, "delivery_date", None))
        if po_date and delivery and delivery < po_date:
            raise serializers.ValidationError({"delivery_date": "Delivery date cannot be before the PO date."})
        customer = attrs.get("customer", getattr(self.instance, "customer", None))
        number = attrs.get("po_number", getattr(self.instance, "po_number", None))
        if customer and number:
            dup = PurchaseOrder.objects.filter(customer=customer, po_number__iexact=number)
            if self.instance:
                dup = dup.exclude(pk=self.instance.pk)
            if dup.exists():
                raise serializers.ValidationError({"po_number": f"PO '{number}' already exists for {customer.name}."})
        items = attrs.get("items")
        if self.instance is None and not items:
            raise serializers.ValidationError({"items": "At least one line item is required."})
        for idx, it in enumerate(items or []):
            if not it["material"].is_active and not it.get("id"):
                raise serializers.ValidationError({"items": f"Line {idx + 1}: material '{it['material'].name}' is inactive."})
        return attrs

    def create(self, validated):
        items = validated.pop("items")
        return services.create_purchase_order(validated, items, self.context["request"].user)

    def update(self, instance, validated):
        items = validated.pop("items", None)
        return services.update_purchase_order(instance, validated, items)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=300)
