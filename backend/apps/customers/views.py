from django.db.models import Count
from rest_framework import viewsets

from apps.accounts.audit import AuditMixin
from apps.accounts.exceptions import Conflict

from .models import Customer
from .serializers import CustomerSerializer


class CustomerViewSet(AuditMixin, viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    search_fields = ["customer_code", "name", "contact_person", "email", "mobile", "gst_number"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "customer_code", "created_at", "po_count"]

    def get_queryset(self):
        return Customer.objects.annotate(po_count=Count("purchase_orders")).order_by("name")

    def perform_destroy(self, instance):
        if instance.purchase_orders.exists():
            raise Conflict(
                f"Cannot delete '{instance.name}': it is linked to {instance.purchase_orders.count()} purchase order(s). "
                "Deactivate the customer instead."
            )
        super().perform_destroy(instance)
