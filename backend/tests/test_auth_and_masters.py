from django.test import Client
from rest_framework.test import APIClient

from .base import API, BaseAPITest


class AuthTests(BaseAPITest):
    def test_unauthenticated_requests_rejected(self):
        c = APIClient()
        for url in ("/customers/", "/materials/", "/purchase-orders/", "/dashboard/summary/", "/reports/summary/"):
            self.assertIn(c.get(API + url).status_code, (401, 403), url)
        self.assertEqual(c.post(API + "/customers/", {}, format="json").status_code, 403)

    def test_health_is_public(self):
        r = APIClient().get(API + "/health/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["database"], "ok")

    def test_login_logout_flow_and_csrf(self):
        c = Client(enforce_csrf_checks=True)
        token = c.get(API + "/auth/csrf/").json()["csrfToken"]
        bad = c.post(API + "/auth/login/", {"username": "admin", "password": "x"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.json()["error"]["code"], "invalid_credentials")
        ok = c.post(API + "/auth/login/", {"username": "admin", "password": "Adm1n-pass-xyz"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.json()["role"], "admin")
        token = c.cookies["csrftoken"].value
        # state-changing request without CSRF token is refused
        self.assertEqual(c.post(API + "/customers/", {"customer_code": "Z", "name": "Z"}, content_type="application/json").status_code, 403)
        with_token = c.post(API + "/customers/", {"customer_code": "Z9", "name": "Zed Co"}, content_type="application/json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(with_token.status_code, 201, with_token.content)
        self.assertEqual(c.post(API + "/auth/logout/", content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 204)
        self.assertEqual(c.get(API + "/customers/").status_code, 403)

    def test_staff_cannot_delete_or_manage_users(self):
        staff = self.as_staff()
        self.assertEqual(staff.get(API + "/customers/").status_code, 200)
        self.assertEqual(staff.delete(f"{API}/customers/{self.customer2.pk}/").status_code, 403)
        self.assertEqual(staff.get(API + "/auth/users/").status_code, 403)
        self.assertEqual(staff.patch(API + "/auth/company/", {"name": "X"}, format="json").status_code, 403)

    def test_admin_manages_users(self):
        r = self.client.post(API + "/auth/users/", {"username": "newbie", "password": "Str0ng-pass-123", "role": "staff"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.json()["role"], "staff")
        weak = self.client.post(API + "/auth/users/", {"username": "weak", "password": "123", "role": "staff"}, format="json")
        self.assertEqual(weak.status_code, 400)
        self.assertEqual(self.client.delete(f"{API}/auth/users/{self.admin.pk}/").status_code, 409)


class CustomerTests(BaseAPITest):
    def test_crud_search_filter_pagination(self):
        r = self.client.post(API + "/customers/", {"customer_code": "c9", "name": "Zeta Corp", "gst_number": "27AABCA1234F1Z5", "mobile": "9822012345", "is_active": True}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        cid = r.json()["id"]
        self.assertEqual(r.json()["customer_code"], "C9")
        self.assertEqual(self.client.patch(f"{API}/customers/{cid}/", {"contact_person": "Zed"}, format="json").json()["contact_person"], "Zed")
        self.assertEqual(self.client.get(API + "/customers/?search=zeta").json()["count"], 1)
        self.client.patch(f"{API}/customers/{cid}/", {"is_active": False}, format="json")
        self.assertEqual(self.client.get(API + "/customers/?is_active=false").json()["count"], 1)
        self.assertEqual(len(self.client.get(API + "/customers/?page_size=1").json()["results"]), 1)
        self.assertEqual(self.client.delete(f"{API}/customers/{cid}/").status_code, 204)

    def test_validation_and_duplicates(self):
        r = self.client.post(API + "/customers/", {"customer_code": "c1", "name": "apex engineering works pvt ltd"}, format="json")
        self.assertEqual(r.status_code, 400)
        err = r.json()["error"]
        self.assertEqual(err["message"], "Validation failed.")
        self.assertIn("customer_code", err["details"])
        self.assertIn("name", err["details"])
        bad = self.client.post(API + "/customers/", {"customer_code": "N1", "name": "New", "gst_number": "BADGST", "mobile": "abc"}, format="json")
        self.assertIn("gst_number", bad.json()["error"]["details"])
        self.assertIn("mobile", bad.json()["error"]["details"])

    def test_delete_blocked_when_pos_exist(self):
        self.create_po()
        r = self.client.delete(f"{API}/customers/{self.customer.pk}/")
        self.assertEqual(r.status_code, 409)
        self.assertIn("Deactivate", r.json()["error"]["message"])


class MaterialTests(BaseAPITest):
    def test_crud_and_protection(self):
        r = self.client.post(API + "/materials/", {"material_code": "m9", "name": "Copper Rod", "uom": "KG", "default_rate": "500.00", "category": "Metal"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        mid = r.json()["id"]
        self.assertEqual(self.client.get(API + "/materials/?category=Metal").json()["count"], 1)
        self.assertEqual(self.client.post(API + "/materials/", {"material_code": "M10", "name": "copper rod", "uom": "KG", "default_rate": "1"}, format="json").status_code, 400)
        self.assertEqual(self.client.post(API + "/materials/", {"material_code": "M11", "name": "Neg", "uom": "KG", "default_rate": "-1"}, format="json").status_code, 400)
        self.create_po()
        self.assertEqual(self.client.delete(f"{API}/materials/{self.bolt.pk}/").status_code, 409)
        self.assertEqual(self.client.delete(f"{API}/materials/{mid}/").status_code, 204)

    def test_alias_mapping(self):
        r = self.client.post(API + "/materials/aliases/", {"material": self.bolt.pk, "description": "HEX BOLT 10x50 ZP"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        dup = self.client.post(API + "/materials/aliases/", {"material": self.plate.pk, "description": "hex bolt 10x50  zp"}, format="json")
        self.assertEqual(dup.status_code, 400)
