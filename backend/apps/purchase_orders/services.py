"""Business rules for purchase orders. All quantities/status derive from SupplyEntry rows."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.exceptions import Conflict

from .models import PurchaseOrder, PurchaseOrderItem

ZERO = Decimal("0")
CENT = Decimal("0.01")


def line_amount(qty, price):
    return (Decimal(qty) * Decimal(price)).quantize(CENT)


def recalc_item_supplied(item):
    """Set item.supplied_quantity from the actual supply transactions."""
    total = item.supply_entries.aggregate(t=Sum("quantity"))["t"] or ZERO
    item.supplied_quantity = total
    item.save(update_fields=["supplied_quantity"])
    return total


def derive_status(po, items=None):
    items = list(items if items is not None else po.items.all())
    if po.status == PurchaseOrder.CANCELLED:
        return PurchaseOrder.CANCELLED
    if items and all(i.supplied_quantity >= i.ordered_quantity for i in items):
        return PurchaseOrder.FULFILLED
    if any(i.supplied_quantity > 0 for i in items):
        return PurchaseOrder.PARTIAL
    return PurchaseOrder.PENDING


def recalc_po(po):
    """Recompute order total and status from the line items / supply history."""
    items = list(po.items.all())
    po.order_total = sum((i.line_amount for i in items), ZERO)
    po.status = derive_status(po, items)
    po.save(update_fields=["order_total", "status", "updated_at"])
    return po


def lock_po(po_id):
    return PurchaseOrder.objects.select_for_update().get(pk=po_id)


def _check_items(items_data):
    if not items_data:
        raise serializers.ValidationError({"items": "At least one line item is required."})


@transaction.atomic
def create_purchase_order(header, items_data, user=None):
    _check_items(items_data)
    po = PurchaseOrder.objects.create(created_by=user, **header)
    for row in items_data:
        row = dict(row)
        row["line_amount"] = line_amount(row["ordered_quantity"], row["unit_price"])
        row.pop("id", None)
        PurchaseOrderItem.objects.create(po=po, **row)
    recalc_po(po)
    return po


@transaction.atomic
def update_purchase_order(po, header, items_data):
    po = lock_po(po.pk)
    if po.status == PurchaseOrder.CANCELLED:
        raise Conflict("A cancelled purchase order cannot be edited. Reopen it first.")
    for k, v in header.items():
        setattr(po, k, v)
    po.save()

    if items_data is not None:
        _check_items(items_data)
        existing = {i.pk: i for i in po.items.select_for_update()}
        keep = set()
        errors = []
        for idx, row in enumerate(items_data):
            row = dict(row)
            item_id = row.pop("id", None)
            row["line_amount"] = line_amount(row["ordered_quantity"], row["unit_price"])
            if item_id:
                item = existing.get(item_id)
                if item is None:
                    raise serializers.ValidationError({"items": f"Line item {item_id} does not belong to this PO."})
                keep.add(item_id)
                supplied = item.supply_entries.aggregate(t=Sum("quantity"))["t"] or ZERO
                if row["ordered_quantity"] < supplied:
                    errors.append(
                        f"Line {idx + 1}: ordered quantity {row['ordered_quantity']} cannot be below already supplied quantity {supplied}."
                    )
                    continue
                if supplied > 0 and row["material"].pk != item.material_id:
                    errors.append(f"Line {idx + 1}: material cannot be changed after supply has been recorded.")
                    continue
                for k, v in row.items():
                    setattr(item, k, v)
                item.supplied_quantity = supplied
                item.save()
            else:
                PurchaseOrderItem.objects.create(po=po, **row)
        for item_id, item in existing.items():
            if item_id not in keep:
                if item.supply_entries.exists():
                    errors.append(f"Line '{item.material.name}' has supply history and cannot be removed.")
                else:
                    item.delete()
        if errors:
            raise serializers.ValidationError({"items": errors})
    recalc_po(po)
    return po


@transaction.atomic
def cancel_purchase_order(po, reason=""):
    po = lock_po(po.pk)
    if po.status == PurchaseOrder.FULFILLED:
        raise Conflict("A fulfilled purchase order cannot be cancelled.")
    if po.status == PurchaseOrder.CANCELLED:
        raise Conflict("Purchase order is already cancelled.")
    po.status = PurchaseOrder.CANCELLED
    po.cancel_reason = reason[:300]
    po.cancelled_at = timezone.now()
    po.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])
    return po


@transaction.atomic
def reopen_purchase_order(po):
    po = lock_po(po.pk)
    if po.status != PurchaseOrder.CANCELLED:
        raise Conflict("Only cancelled purchase orders can be reopened.")
    po.status = PurchaseOrder.PENDING
    po.cancel_reason = ""
    po.cancelled_at = None
    po.status = derive_status(po)
    po.save(update_fields=["status", "cancel_reason", "cancelled_at", "updated_at"])
    return po


@transaction.atomic
def delete_purchase_order(po):
    po = lock_po(po.pk)
    from apps.supply_tracking.models import SupplyEntry

    if SupplyEntry.objects.filter(po=po).exists():
        raise Conflict("This purchase order has supply history and cannot be deleted. Cancel it instead.")
    # release linked inbox message / OCR extraction so they can be re-processed
    from apps.inbox.models import InboxMessage
    from apps.ocr.models import OCRExtraction

    OCRExtraction.objects.filter(linked_po=po).update(linked_po=None, status=OCRExtraction.PROCESSED)
    InboxMessage.objects.filter(converted_po=po).update(converted_po=None, status=InboxMessage.SCANNED)
    po.delete()
