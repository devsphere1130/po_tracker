from decimal import Decimal

from .base import API, BaseAPITest


class ReportTests(BaseAPITest):
    def setUp(self):
        super().setUp()
        self.po1 = self.create_po("R-1")
        self.po2 = self.create_po("R-2", customer=self.customer2, items=[
            {"material": self.bolt.pk, "ordered_quantity": "10", "uom": "NOS", "unit_price": "10"}])
        self.supply(self.po1, self.po1["items"][0], 40)
        self.supply(self.po2, self.po2["items"][0], 10)

    def test_dashboard_live_values(self):
        d = self.client.get(API + "/dashboard/summary/").json()
        self.assertEqual((d["total_pos"], d["partial"], d["fulfilled"], d["pending"], d["cancelled"]), (2, 1, 1, 0, 0))
        self.assertEqual(Decimal(d["active_value"]), Decimal("4650.00"))
        self.assertEqual(Decimal(d["pending_value"]), Decimal("750") + Decimal("3400"))  # 60 bolts*12.5 + 50 plates*68
        self.assertEqual(len(d["recent_supplies"]), 2)
        self.assertEqual(len(d["customer_summary"]), 2)
        self.client.post(f"{API}/purchase-orders/{self.po1['id']}/cancel/", {}, format="json")
        d2 = self.client.get(API + "/dashboard/summary/").json()
        self.assertEqual((d2["cancelled"], d2["partial"]), (1, 0))
        self.assertEqual(Decimal(d2["active_value"]), Decimal("0"))

    def test_customer_reports(self):
        r = self.client.get(API + "/reports/customers/?ordering=value").json()
        self.assertEqual(r["rows"][0]["customer"], self.customer.name)
        self.assertEqual(Decimal(r["rows"][0]["total_value"]), Decimal("4650.00"))
        self.assertEqual(self.client.get(API + f"/reports/customers/?customer={self.customer2.pk}").json()["rows"][0]["po_count"], 1)

    def test_material_report_groups_by_unit_and_updates(self):
        rows = {x["material"]: x for x in self.client.get(API + "/reports/materials/").json()["rows"]}
        bolt = rows[self.bolt.name]
        self.assertEqual((Decimal(bolt["ordered"]), Decimal(bolt["supplied"]), Decimal(bolt["pending"])), (Decimal("110"), Decimal("50"), Decimal("60")))
        self.assertEqual(bolt["uom"], "NOS")
        self.supply(self.po1, self.po1["items"][0], 60)
        again = {x["material"]: x for x in self.client.get(API + "/reports/materials/").json()["rows"]}
        self.assertEqual(Decimal(again[self.bolt.name]["pending"]), Decimal("0"))

    def test_po_status_reports_and_filters(self):
        self.assertEqual(len(self.client.get(API + "/reports/po-status/partial/").json()["rows"]), 1)
        self.assertEqual(len(self.client.get(API + "/reports/po-status/fulfilled/").json()["rows"]), 1)
        self.assertEqual(len(self.client.get(API + "/reports/po-status/pending/").json()["rows"]), 0)
        self.assertEqual(len(self.client.get(API + "/reports/po-status/overdue/").json()["rows"]), 0)
        self.assertEqual(self.client.get(API + "/reports/po-status/bogus/").status_code, 400)
        self.assertEqual(self.client.get(API + "/reports/summary/?date_from=2999-01-01").json()["total_pos"], 0)
        self.assertEqual(self.client.get(API + "/reports/summary/?date_from=nope").status_code, 400)
        self.assertEqual(self.client.get(API + f"/reports/summary/?material={self.plate.pk}").json()["total_pos"], 1)

    def test_monthly_and_csv_export(self):
        m = self.client.get(API + "/reports/monthly/").json()
        self.assertEqual(m["rows"][0]["po_count"], 2)
        r = self.client.get(API + "/reports/customers/?export=csv")
        self.assertEqual(r["Content-Type"], "text/csv")
        text = r.content.decode("utf-8-sig")
        self.assertTrue(text.startswith("Customer,PO count"))
        self.assertIn(self.customer.name, text)
        self.assertEqual(self.client.get(API + "/reports/nonsense/").status_code, 404)
