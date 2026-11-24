from datetime import date, timedelta
from decimal import Decimal

from apps.purchase_orders.models import PurchaseOrder

from .base import API, BaseAPITest


class PurchaseOrderTests(BaseAPITest):
    def test_create_multi_item_po_calculates_totals(self):
        po = self.create_po()
        self.assertEqual(po["status"], "pending")
        self.assertEqual(Decimal(po["order_total"]), Decimal("4650.00"))
        self.assertEqual([Decimal(i["line_amount"]) for i in po["items"]], [Decimal("1250.00"), Decimal("3400.00")])
        self.assertEqual(Decimal(po["items"][0]["pending_quantity"]), Decimal("100"))

    def test_server_ignores_client_supplied_totals_and_status(self):
        body = self.po_payload()
        body["order_total"] = "1.00"
        body["status"] = "fulfilled"
        r = self.client.post(API + "/purchase-orders/", body, format="json")
        self.assertEqual(r.json()["status"], "pending")
        self.assertEqual(Decimal(r.json()["order_total"]), Decimal("4650.00"))

    def test_validation_rules(self):
        self.create_po(number="DUP-1")
        dup = self.client.post(API + "/purchase-orders/", self.po_payload("dup-1"), format="json")
        self.assertEqual(dup.status_code, 400)
        self.assertIn("po_number", dup.json()["error"]["details"])
        # same number is allowed for another customer
        self.assertEqual(self.client.post(API + "/purchase-orders/", self.po_payload("DUP-1", customer=self.customer2), format="json").status_code, 201)
        self.assertEqual(self.client.post(API + "/purchase-orders/", self.po_payload("X1", items=[]), format="json").status_code, 400)
        bad_date = self.po_payload("X2", delivery_date=(date.today() - timedelta(days=5)).isoformat())
        self.assertIn("delivery_date", self.client.post(API + "/purchase-orders/", bad_date, format="json").json()["error"]["details"])
        zero = self.po_payload("X3", items=[{"material": self.bolt.pk, "ordered_quantity": "0", "uom": "NOS", "unit_price": "1"}])
        self.assertEqual(self.client.post(API + "/purchase-orders/", zero, format="json").status_code, 400)

    def test_edit_header_and_items(self):
        po = self.create_po()
        items = po["items"]
        items[0]["ordered_quantity"] = "200"
        new_line = {"material": self.bolt.pk, "original_description": "Extra", "ordered_quantity": "10", "uom": "NOS", "unit_price": "2"}
        r = self.client.patch(f"{API}/purchase-orders/{po['id']}/", {"notes": "edited", "items": [items[0], new_line]}, format="json")
        self.assertEqual(r.status_code, 200, r.content)
        body = r.json()
        self.assertEqual(len(body["items"]), 2)  # plate line removed (no supply), new line added
        self.assertEqual(Decimal(body["order_total"]), Decimal("200") * Decimal("12.50") + Decimal("20"))
        self.assertEqual(body["notes"], "edited")

    def test_filters_and_search(self):
        self.create_po("A-1")
        self.create_po("B-1", customer=self.customer2)
        self.assertEqual(self.client.get(f"{API}/purchase-orders/?customer={self.customer2.pk}").json()["count"], 1)
        self.assertEqual(self.client.get(f"{API}/purchase-orders/?search=A-1").json()["count"], 1)
        self.assertEqual(self.client.get(f"{API}/purchase-orders/?status=pending&status=partial").json()["count"], 2)
        self.assertEqual(self.client.get(f"{API}/purchase-orders/?status=fulfilled").json()["count"], 0)
        self.assertEqual(self.client.get(f"{API}/purchase-orders/?material={self.plate.pk}").json()["count"], 2)
        self.assertEqual(self.client.get(f"{API}/purchase-orders/?po_date_from=2999-01-01").json()["count"], 0)

    def test_delete_rules(self):
        po = self.create_po("DEL-1")
        self.assertEqual(self.as_staff().delete(f"{API}/purchase-orders/{po['id']}/").status_code, 403)
        self.assertEqual(self.client.delete(f"{API}/purchase-orders/{po['id']}/").status_code, 204)
        po2 = self.create_po("DEL-2")
        self.assertEqual(self.supply(po2, po2["items"][0], 5).status_code, 201)
        r = self.client.delete(f"{API}/purchase-orders/{po2['id']}/")
        self.assertEqual(r.status_code, 409)
        self.assertIn("supply history", r.json()["error"]["message"])


class SupplyTrackingTests(BaseAPITest):
    def get(self, po):
        return self.client.get(f"{API}/purchase-orders/{po['id']}/").json()

    def test_full_lifecycle_pending_partial_fulfilled(self):
        po = self.create_po()
        bolt, plate = po["items"]
        r = self.supply(po, bolt, 40, challan_number="DC-1")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Decimal(r.json()["item_pending_quantity"]), Decimal("60"))
        cur = self.get(po)
        self.assertEqual(cur["status"], "partial")
        self.assertEqual(Decimal(cur["items"][0]["supplied_quantity"]), Decimal("40"))
        self.assertEqual(Decimal(cur["items"][0]["pending_quantity"]), Decimal("60"))
        self.assertEqual(cur["items"][0]["progress_percent"], 40.0)
        self.assertEqual(len(cur["supply_entries"]), 1)
        self.assertEqual(self.supply(po, bolt, 60).status_code, 201)  # multiple supplies on one line
        self.assertEqual(self.get(po)["status"], "partial")  # plate still outstanding
        self.assertEqual(self.supply(po, plate, 50).status_code, 201)
        done = self.get(po)
        self.assertEqual(done["status"], "fulfilled")
        self.assertEqual(done["progress_percent"], 100.0)
        self.assertEqual(len(done["supply_entries"]), 3)

    def test_oversupply_and_invalid_quantity_rejected(self):
        po = self.create_po()
        bolt = po["items"][0]
        self.supply(po, bolt, 90)
        over = self.supply(po, bolt, 11)
        self.assertEqual(over.status_code, 400)
        self.assertIn("exceeds pending", str(over.json()))
        self.assertEqual(self.supply(po, bolt, 0).status_code, 400)
        self.assertEqual(self.supply(po, bolt, -5).status_code, 400)
        self.assertEqual(self.supply(po, bolt, 10).status_code, 201)  # exactly the balance is fine
        self.assertEqual(Decimal(self.get(po)["items"][0]["supplied_quantity"]), Decimal("100"))

    def test_line_from_another_po_rejected(self):
        po1, po2 = self.create_po("P1"), self.create_po("P2")
        self.assertEqual(self.supply(po1, po2["items"][0], 1).status_code, 400)

    def test_edit_and_delete_supply_recalculates(self):
        po = self.create_po()
        bolt = po["items"][0]
        entry = self.supply(po, bolt, 30).json()
        self.assertEqual(self.client.patch(f"{API}/supply-entries/{entry['id']}/", {"quantity": "100"}, format="json").status_code, 200)
        self.assertEqual(Decimal(self.get(po)["items"][0]["pending_quantity"]), Decimal("0"))
        self.assertEqual(self.client.patch(f"{API}/supply-entries/{entry['id']}/", {"quantity": "101"}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(f"{API}/supply-entries/{entry['id']}/").status_code, 204)
        after = self.get(po)
        self.assertEqual(after["status"], "pending")
        self.assertEqual(Decimal(after["items"][0]["supplied_quantity"]), Decimal("0"))

    def test_cannot_reduce_ordered_below_supplied(self):
        po = self.create_po()
        self.supply(po, po["items"][0], 60)
        items = po["items"]
        items[0]["ordered_quantity"] = "50"
        r = self.client.patch(f"{API}/purchase-orders/{po['id']}/", {"items": items}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("below already supplied", str(r.json()))
        items[0]["ordered_quantity"] = "60"  # exactly the supplied quantity is allowed
        self.assertEqual(self.client.patch(f"{API}/purchase-orders/{po['id']}/", {"items": items}, format="json").status_code, 200)
        r = self.client.patch(f"{API}/purchase-orders/{po['id']}/", {"items": items[1:]}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("supply history", str(r.json()))

    def test_cancel_and_reopen(self):
        po = self.create_po()
        self.supply(po, po["items"][0], 10)
        r = self.client.post(f"{API}/purchase-orders/{po['id']}/cancel/", {"reason": "Customer request"}, format="json")
        self.assertEqual(r.json()["status"], "cancelled")
        self.assertEqual(self.supply(po, po["items"][0], 1).status_code, 409)
        self.assertEqual(self.client.patch(f"{API}/purchase-orders/{po['id']}/", {"notes": "x"}, format="json").status_code, 409)
        reopened = self.client.post(f"{API}/purchase-orders/{po['id']}/reopen/").json()
        self.assertEqual(reopened["status"], "partial")  # derived from the real supply history

    def test_fulfilled_po_cannot_be_cancelled(self):
        po = self.create_po(items=[{"material": self.bolt.pk, "ordered_quantity": "5", "uom": "NOS", "unit_price": "1"}])
        self.supply(po, po["items"][0], 5)
        self.assertEqual(self.client.post(f"{API}/purchase-orders/{po['id']}/cancel/", {}, format="json").status_code, 409)

    def test_overdue_flag_and_filter(self):
        po = self.create_po("OD-1")
        PurchaseOrder.objects.filter(pk=po["id"]).update(po_date=date.today() - timedelta(days=30), delivery_date=date.today() - timedelta(days=2))
        listing = self.client.get(f"{API}/purchase-orders/?overdue=true").json()
        self.assertEqual(listing["count"], 1)
        self.assertTrue(listing["results"][0]["is_overdue"])
        self.assertEqual(self.client.get(f"{API}/dashboard/summary/").json()["overdue"], 1)

    def test_db_constraint_blocks_oversupply_even_outside_api(self):
        from django.db import IntegrityError, transaction
        from apps.purchase_orders.models import PurchaseOrderItem

        po = self.create_po()
        with self.assertRaises(IntegrityError), transaction.atomic():
            PurchaseOrderItem.objects.filter(pk=po["items"][0]["id"]).update(supplied_quantity=Decimal("101"))
