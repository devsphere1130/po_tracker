from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Upper
from django.utils import timezone


class PurchaseOrder(models.Model):
    PENDING, PARTIAL, FULFILLED, CANCELLED = "pending", "partial", "fulfilled", "cancelled"
    STATUS_CHOICES = [(PENDING, "Pending"), (PARTIAL, "Partial"), (FULFILLED, "Fulfilled"), (CANCELLED, "Cancelled")]
    SOURCE_CHOICES = [("manual", "Manual"), ("email", "Email"), ("upload", "Upload")]

    po_number = models.CharField(max_length=60)
    customer = models.ForeignKey("customers.Customer", on_delete=models.PROTECT, related_name="purchase_orders")
    po_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default="manual")
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to="purchase_orders/", null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=PENDING)
    order_total = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    cancel_reason = models.CharField(max_length=300, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-po_date", "-id"]
        constraints = [
            models.UniqueConstraint(Upper("po_number"), "customer", name="uniq_po_number_per_customer"),
            models.CheckConstraint(
                condition=Q(delivery_date__isnull=True) | Q(delivery_date__gte=F("po_date")), name="po_delivery_after_po_date"
            ),
            models.CheckConstraint(condition=Q(order_total__gte=0), name="po_total_non_negative"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["po_date"]),
            models.Index(fields=["delivery_date"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return f"{self.po_number} ({self.customer.name})"

    @property
    def is_overdue(self):
        return bool(
            self.delivery_date
            and self.delivery_date < timezone.localdate()
            and self.status in (self.PENDING, self.PARTIAL)
        )


class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    material = models.ForeignKey("materials.Material", on_delete=models.PROTECT, related_name="po_items")
    original_description = models.CharField(max_length=400, blank=True)
    ordered_quantity = models.DecimalField(max_digits=14, decimal_places=3)
    uom = models.CharField(max_length=10)
    unit_price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    line_amount = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.00"))
    # Cache recalculated from SupplyEntry rows only (never edited by hand).
    supplied_quantity = models.DecimalField(max_digits=14, decimal_places=3, default=Decimal("0.000"))

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=Q(ordered_quantity__gt=0), name="item_ordered_qty_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="item_price_non_negative"),
            models.CheckConstraint(condition=Q(supplied_quantity__gte=0), name="item_supplied_non_negative"),
            models.CheckConstraint(condition=Q(supplied_quantity__lte=F("ordered_quantity")), name="item_supplied_le_ordered"),
        ]
        indexes = [models.Index(fields=["po", "material"])]

    def __str__(self):
        return f"{self.po.po_number}: {self.material.name}"

    @property
    def pending_quantity(self):
        return self.ordered_quantity - self.supplied_quantity

    @property
    def progress_percent(self):
        if not self.ordered_quantity:
            return 0.0
        return float(round(min(self.supplied_quantity / self.ordered_quantity, 1) * 100, 1))
