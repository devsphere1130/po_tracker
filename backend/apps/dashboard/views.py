from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem
from apps.supply_tracking.models import SupplyEntry

ZERO = Decimal("0")


class DashboardSummaryView(APIView):
    """All figures are computed live from the database on every request."""

    def get(self, request):
        today = timezone.localdate()
        counts = {s: 0 for s, _ in PurchaseOrder.STATUS_CHOICES}
        for r in PurchaseOrder.objects.values("status").annotate(n=Count("id")):
            counts[r["status"]] = r["n"]
        active = PurchaseOrder.objects.filter(status__in=["pending", "partial"])
        active_value = active.aggregate(v=Sum("order_total"))["v"] or ZERO
        pending_expr = ExpressionWrapper((F("ordered_quantity") - F("supplied_quantity")) * F("unit_price"), output_field=DecimalField())
        pending_value = PurchaseOrderItem.objects.filter(po__status__in=["pending", "partial"]).aggregate(v=Sum(pending_expr))["v"] or ZERO
        overdue = active.filter(delivery_date__lt=today).count()

        recent_pos = [
            {"id": p.id, "po_number": p.po_number, "customer_name": p.customer.name, "po_date": p.po_date, "status": p.status,
             "order_total": p.order_total, "delivery_date": p.delivery_date, "is_overdue": p.is_overdue}
            for p in PurchaseOrder.objects.select_related("customer").order_by("-created_at", "-id")[:6]
        ]
        recent_supplies = [
            {"id": s.id, "po": s.po_id, "po_number": s.po.po_number, "customer_name": s.po.customer.name,
             "material_name": s.item.material.name, "quantity": s.quantity, "uom": s.item.uom, "supply_date": s.supply_date,
             "challan_number": s.challan_number}
            for s in SupplyEntry.objects.select_related("po__customer", "item__material").order_by("-supply_date", "-id")[:6]
        ]
        customer_summary = self._customer_summary()
        trend = [
            {"month": r["m"].strftime("%Y-%m"), "po_count": r["n"], "total_value": r["v"] or ZERO}
            for r in PurchaseOrder.objects.annotate(m=TruncMonth("po_date")).values("m").annotate(n=Count("id"), v=Sum("order_total")).order_by("m")
        ][-12:]
        return Response({
            "total_pos": sum(counts.values()), "pending": counts["pending"], "partial": counts["partial"],
            "fulfilled": counts["fulfilled"], "cancelled": counts["cancelled"], "overdue": overdue,
            "active_value": active_value, "pending_value": pending_value,
            "recent_pos": recent_pos, "recent_supplies": recent_supplies,
            "customer_summary": customer_summary, "monthly_trend": trend,
        })

    @staticmethod
    def _customer_summary():
        from django.db.models import Q

        qs = (PurchaseOrder.objects.exclude(status="cancelled").values("customer_id", "customer__name")
              .annotate(n=Count("id"), v=Sum("order_total"), open=Count("id", filter=Q(status__in=["pending", "partial"])))
              .order_by("-v")[:8])
        return [{"customer_id": r["customer_id"], "customer": r["customer__name"], "po_count": r["n"],
                 "total_value": r["v"] or ZERO, "open_count": r["open"]} for r in qs]
