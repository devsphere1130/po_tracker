"""Transaction-safe supply recording. The PO row is locked (SELECT ... FOR UPDATE) so two
concurrent requests can never both consume the same pending balance."""
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from apps.accounts.exceptions import Conflict
from apps.purchase_orders import services as po_services
from apps.purchase_orders.models import PurchaseOrder, PurchaseOrderItem

from .models import SupplyEntry

ZERO = Decimal("0")


def _supplied(item, exclude_entry_id=None):
    qs = item.supply_entries.all()
    if exclude_entry_id:
        qs = qs.exclude(pk=exclude_entry_id)
    return qs.aggregate(t=Sum("quantity"))["t"] or ZERO


def _validate(po, item, quantity, supply_date, exclude_entry_id=None):
    if po.status == PurchaseOrder.CANCELLED:
        raise Conflict("Cannot record supply against a cancelled purchase order.")
    if item.po_id != po.pk:
        raise serializers.ValidationError({"item": "Line item does not belong to this purchase order."})
    if quantity is None or quantity <= 0:
        raise serializers.ValidationError({"quantity": "Supplied quantity must be greater than zero."})
    if supply_date < po.po_date:
        raise serializers.ValidationError({"supply_date": "Supply date cannot be before the PO date."})
    pending = item.ordered_quantity - _supplied(item, exclude_entry_id)
    if quantity > pending:
        raise serializers.ValidationError(
            {"quantity": f"Supplied quantity {quantity} exceeds pending quantity {pending} for '{item.material.name}'."}
        )


def _refresh(po, *item_ids):
    for item in PurchaseOrderItem.objects.filter(pk__in=set(item_ids)):
        po_services.recalc_item_supplied(item)
    po_services.recalc_po(po)


@transaction.atomic
def record_supply(po, item, supply_date, quantity, challan_number="", remarks="", user=None):
    po = po_services.lock_po(po.pk)
    item = PurchaseOrderItem.objects.select_for_update().select_related("material").get(pk=item.pk)
    _validate(po, item, quantity, supply_date)
    entry = SupplyEntry.objects.create(
        po=po, item=item, supply_date=supply_date, quantity=quantity,
        challan_number=challan_number, remarks=remarks, created_by=user,
    )
    _refresh(po, item.pk)
    return _fresh(entry)


@transaction.atomic
def update_supply(entry, data):
    po = po_services.lock_po(entry.po_id)
    old_item_id = entry.item_id
    item = PurchaseOrderItem.objects.select_for_update().select_related("material").get(pk=data.get("item", entry.item).pk)
    quantity = data.get("quantity", entry.quantity)
    supply_date = data.get("supply_date", entry.supply_date)
    _validate(po, item, quantity, supply_date, exclude_entry_id=entry.pk)
    entry.item = item
    entry.quantity = quantity
    entry.supply_date = supply_date
    entry.challan_number = data.get("challan_number", entry.challan_number)
    entry.remarks = data.get("remarks", entry.remarks)
    entry.save()
    _refresh(po, item.pk, old_item_id)
    return _fresh(entry)


@transaction.atomic
def delete_supply(entry):
    po = po_services.lock_po(entry.po_id)
    if po.status == PurchaseOrder.CANCELLED:
        raise Conflict("Supply entries of a cancelled purchase order cannot be deleted. Reopen the PO first.")
    item_id = entry.item_id
    entry.delete()
    _refresh(po, item_id)


def _fresh(entry):
    return SupplyEntry.objects.select_related("po__customer", "item__material").get(pk=entry.pk)
