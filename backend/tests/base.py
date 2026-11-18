from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase

from apps.customers.models import Customer
from apps.materials.models import Material

User = get_user_model()
API = "/api/v1"


class BaseAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", "a@example.com", "Adm1n-pass-xyz")
        cls.staff = User.objects.create_user("staff", "s@example.com", "St4ff-pass-xyz")
        cls.customer = Customer.objects.create(customer_code="C1", name="Apex Engineering Works Pvt Ltd")
        cls.customer2 = Customer.objects.create(customer_code="C2", name="Bharat Auto Components Ltd")
        cls.bolt = Material.objects.create(material_code="M1", name="Hex Bolt M10x50 Zinc Plated", uom="NOS", default_rate="12.50")
        cls.plate = Material.objects.create(material_code="M2", name="MS Plate 10mm", uom="KG", default_rate="68")

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def as_staff(self):
        c = APIClient()
        c.force_authenticate(self.staff)
        return c

    def po_payload(self, number="PO-1", customer=None, items=None, **extra):
        today = date.today()
        body = {
            "po_number": number, "customer": (customer or self.customer).pk, "po_date": today.isoformat(),
            "delivery_date": (today + timedelta(days=10)).isoformat(), "notes": "",
            "items": items if items is not None else [
                {"material": self.bolt.pk, "original_description": "Hex Bolt", "ordered_quantity": "100", "uom": "NOS", "unit_price": "12.50"},
                {"material": self.plate.pk, "original_description": "MS Plate", "ordered_quantity": "50", "uom": "KG", "unit_price": "68.00"},
            ],
        }
        body.update(extra)
        return body

    def create_po(self, number="PO-1", **kw):
        r = self.client.post(f"{API}/purchase-orders/", self.po_payload(number, **kw), format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()

    def supply(self, po, item, qty, **kw):
        body = {"po": po["id"], "item": item["id"], "supply_date": date.today().isoformat(), "quantity": str(qty)}
        body.update(kw)
        return self.client.post(f"{API}/supply-entries/", body, format="json")
