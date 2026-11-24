from django.conf import settings
from django.db import models
from django.db.models import Q


class SupplyEntry(models.Model):
    po = models.ForeignKey("purchase_orders.PurchaseOrder", on_delete=models.CASCADE, related_name="supply_entries")
    item = models.ForeignKey("purchase_orders.PurchaseOrderItem", on_delete=models.CASCADE, related_name="supply_entries")
    supply_date = models.DateField()
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    challan_number = models.CharField(max_length=60, blank=True)
    remarks = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-supply_date", "-id"]
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name="supply_qty_positive")]
        indexes = [
            models.Index(fields=["po", "supply_date"]),
            models.Index(fields=["item"]),
            models.Index(fields=["supply_date"]),
        ]

    def __str__(self):
        return f"{self.po.po_number} {self.item.material.name} x {self.quantity} on {self.supply_date}"
