"""Report queries. Everything is computed live from PurchaseOrder / PurchaseOrderItem / SupplyEntry rows.
Quantities are grouped by (material, UOM) and never summed across different units."""
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem

ZERO = Decimal("0")
VALID_STATUS = {"pending", "partial", "fulfilled", "cancelled"}


def _date(params, key):
    from datetime import date

    v = params.get(key)
    if not v:
        return None
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise ValidationError({key: "Use YYYY-MM-DD."})


def _int(params, key):
    v = params.get(key)
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        raise ValidationError({key: "Must be a number."})


def po_filter_q(params, prefix="", default_exclude_cancelled=False):
    """Q object over PurchaseOrder fields (prefix 'po__' when querying items)."""
    q = Q()
    if (d := _date(params, "date_from")):
        q &= Q(**{f"{prefix}po_date__gte": d})
    if (d := _date(params, "date_to")):
        q &= Q(**{f"{prefix}po_date__lte": d})
    if (c := _int(params, "customer")):
        q &= Q(**{f"{prefix}customer_id": c})
    statuses = [s for s in (params.get("status") or "").split(",") if s]
    bad = set(statuses) - VALID_STATUS
    if bad:
        raise ValidationError({"status": f"Unknown status: {', '.join(sorted(bad))}"})
    if statuses:
        q &= Q(**{f"{prefix}status__in": statuses})
    elif default_exclude_cancelled:
        q &= ~Q(**{f"{prefix}status": "cancelled"})
    return q


def pos(params, **kw):
    qs = PurchaseOrder.objects.filter(po_filter_q(params, **kw))
    if (m := _int(params, "material")):
        qs = qs.filter(items__material_id=m).distinct()
    return qs


def items(params, **kw):
    qs = PurchaseOrderItem.objects.filter(po_filter_q(params, prefix="po__", **kw))
    if (m := _int(params, "material")):
        qs = qs.filter(material_id=m)
    return qs


def _limit(params, rows):
    n = _int(params, "limit")
    return rows[:n] if n else rows


def summary(params):
    qs = pos(params)
    by_status = {s: 0 for s in VALID_STATUS}
    for row in qs.values("status").annotate(n=Count("id")):
        by_status[row["status"]] = row["n"]
    total_value = items(params).aggregate(v=Sum("line_amount"))["v"] or ZERO
    today = timezone.localdate()
    overdue = qs.filter(delivery_date__lt=today, status__in=["pending", "partial"]).count()
    return {
        "columns": [], "rows": [],
        "total_pos": sum(by_status.values()), "by_status": by_status, "overdue": overdue, "total_value": total_value,
        "active_customers": qs.values("customer").distinct().count(),
    }


def customers(params):
    ordering = params.get("ordering", "value")
    rows = [
        {"customer_id": r["po__customer_id"], "customer": r["po__customer__name"], "po_count": r["n"], "total_value": r["v"] or ZERO}
        for r in items(params).values("po__customer_id", "po__customer__name").annotate(n=Count("po_id", distinct=True), v=Sum("line_amount"))
    ]
    rows.sort(key=lambda r: (r["po_count"] if ordering == "count" else r["total_value"]), reverse=True)
    cols = [("customer", "Customer"), ("po_count", "PO count"), ("total_value", "Order value (₹)")]
    return {"columns": cols, "rows": _limit(params, rows)}


def materials(params):
    """Excludes cancelled POs unless a status filter is given explicitly."""
    pending_expr = ExpressionWrapper(F("ordered_quantity") - F("supplied_quantity"), output_field=DecimalField())
    qs = items(params, default_exclude_cancelled=True).values("material_id", "material__material_code", "material__name", "uom").annotate(
        ordered=Sum("ordered_quantity"), supplied=Sum("supplied_quantity"), pending=Sum(pending_expr),
        value=Sum("line_amount"), po_count=Count("po_id", distinct=True),
    )
    rows = [
        {"material_id": r["material_id"], "material_code": r["material__material_code"], "material": r["material__name"],
         "uom": r["uom"], "ordered": r["ordered"], "supplied": r["supplied"], "pending": r["pending"],
         "order_value": r["value"], "po_count": r["po_count"]}
        for r in qs
    ]
    order_key = {"ordered": "ordered", "supplied": "supplied", "pending": "pending"}.get(params.get("ordering"), "ordered")
    rows.sort(key=lambda r: r[order_key], reverse=True)
    cols = [("material_code", "Code"), ("material", "Material"), ("uom", "UOM"), ("ordered", "Ordered"), ("supplied", "Supplied"),
            ("pending", "Pending"), ("order_value", "Order value (₹)"), ("po_count", "POs")]
    return {"columns": cols, "rows": _limit(params, rows)}


def po_list(params, kind):
    today = timezone.localdate()
    p = dict(params.items())
    if kind == "overdue":
        qs = pos({**p, "status": ""}).filter(delivery_date__lt=today, status__in=["pending", "partial"])
    else:
        if kind not in ("pending", "partial", "fulfilled", "cancelled"):
            raise ValidationError({"kind": "Unknown PO report."})
        qs = pos({**p, "status": kind})
    qs = qs.select_related("customer").prefetch_related("items").order_by("delivery_date", "po_date")
    rows = []
    for po in qs:
        its = list(po.items.all())
        progress = round(sum(i.progress_percent for i in its) / len(its), 1) if its else 0
        rows.append({
            "id": po.id, "po_number": po.po_number, "customer": po.customer.name, "po_date": po.po_date,
            "delivery_date": po.delivery_date, "status": po.status, "order_total": po.order_total, "progress_percent": progress,
            "days_overdue": (today - po.delivery_date).days if po.delivery_date and po.delivery_date < today and po.status in ("pending", "partial") else 0,
        })
    cols = [("po_number", "PO number"), ("customer", "Customer"), ("po_date", "PO date"), ("delivery_date", "Delivery date"),
            ("status", "Status"), ("order_total", "Order total (₹)"), ("progress_percent", "Progress %"), ("days_overdue", "Days overdue")]
    return {"columns": cols, "rows": rows}


def monthly(params):
    rows = [
        {"month": r["m"].strftime("%Y-%m"), "po_count": r["n"], "total_value": r["v"] or ZERO}
        for r in items(params).annotate(m=TruncMonth("po__po_date")).values("m").annotate(n=Count("po_id", distinct=True), v=Sum("line_amount")).order_by("m")
    ]
    return {"columns": [("month", "Month"), ("po_count", "PO count"), ("total_value", "Order value (₹)")], "rows": rows}


REPORTS = {
    "customers": customers,
    "materials": materials,
    "monthly": monthly,
}
