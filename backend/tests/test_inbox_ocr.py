from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.inbox import demo_documents
from apps.inbox.models import InboxMessage
from apps.ocr.extractor import tesseract_info
from apps.ocr.parser import parse_po_text

from .base import API, BaseAPITest

PO_LINES = [
    "PURCHASE ORDER", "Buyer: Apex Engineering Works Pvt Ltd", "PO Number: APX/9/001", "PO Date: 01/11/2026",
    "Delivery Date: 15/11/2026", "Sr  Description  Qty  Unit  Rate  Amount",
    "1  Hex Bolt M10x50 Zinc Plated  100  Nos  12.50  1,250.00",
    "2  MS Plate 10mm  50  Kg  68.00  3,400.00", "Grand Total: 4,650.00",
]


class ParserTests(BaseAPITest):
    def test_parser_extracts_fields_and_flags_gaps(self):
        out = parse_po_text("\n".join(PO_LINES), [(self.customer.pk, self.customer.name)], [(self.bolt.pk, self.bolt.name, "M1")])
        h = out["header"]
        self.assertEqual(h["po_number"]["value"], "APX/9/001")
        self.assertEqual(h["po_date"]["value"], "2026-11-01")
        self.assertEqual(h["delivery_date"]["value"], "2026-11-15")
        self.assertEqual(h["po_total"]["value"], "4650.00")
        self.assertEqual(h["customer_name"]["matched_customer_id"], self.customer.pk)
        self.assertEqual(len(out["items"]), 2)
        self.assertEqual(out["items"][0]["material_id"], self.bolt.pk)
        self.assertIn("material_unmapped", out["items"][1]["flags"])

    def test_missing_data_is_never_fabricated(self):
        out = parse_po_text("Some random letter without order details\nThanks")
        self.assertEqual(out["items"], [])
        for f in out["header"].values():
            self.assertIsNone(f["value"])
            self.assertEqual(f["status"], "missing")

    def test_inconsistent_line_total_is_flagged(self):
        out = parse_po_text("PO No: A100\n1  Widget Thing  10  Nos  5.00  999.00")
        self.assertIn("line_total_mismatch", out["items"][0]["flags"])


@override_settings(INBOX_MODE="demo", GMAIL_CLIENT_ID="", GMAIL_CLIENT_SECRET="")
class InboxFlowTests(BaseAPITest):
    def test_sync_is_idempotent_and_never_imports_twice(self):
        first = self.client.post(API + "/inbox/messages/sync/", {"provider": "demo"}, format="json").json()
        self.assertEqual(first["imported"], 8)
        second = self.client.post(API + "/inbox/messages/sync/", {"provider": "demo"}, format="json").json()
        self.assertEqual((second["imported"], second["already_imported"]), (0, 8))
        self.assertEqual(InboxMessage.objects.count(), 8)

    def test_live_providers_refuse_without_oauth(self):
        r = self.client.post(API + "/inbox/messages/sync/", {"provider": "gmail"}, format="json")
        self.assertEqual(r.status_code, 409)
        conns = self.client.get(API + "/inbox/connections/").json()["connections"]
        states = {c["provider"]: c["state"] for c in conns}
        self.assertEqual(states["gmail"], "disconnected")
        gmail_id = [c for c in conns if c["provider"] == "gmail"][0]["id"]
        self.assertEqual(self.client.post(f"{API}/inbox/connections/{gmail_id}/connect/").status_code, 409)

    def test_simulate_scan_verify_create_po_and_release(self):
        msg = self.client.post(API + "/inbox/messages/simulate/").json()
        self.assertEqual(msg["status"], "new")
        self.assertEqual(msg["attachments"][0]["content_type"], "application/pdf")
        self.assertEqual(self.client.get(msg["attachments"][0]["file_url"]).status_code, 200)  # preview served
        ex = self.client.post(f"{API}/inbox/messages/{msg['id']}/scan/").json()
        self.assertEqual(ex["status"], "processed", ex)
        self.assertEqual(ex["engine"], "pdf-text")
        form = ex["working_data"]
        self.assertTrue(form["po_number"])
        self.assertEqual(self.client.post(f"{API}/ocr/extractions/{ex['id']}/create-po/").status_code, 409)  # not verified
        for it in form["items"]:
            it["material"] = None
        form["customer"] = None
        self.assertEqual(self.client.post(f"{API}/ocr/extractions/{ex['id']}/verify/", form, format="json").status_code, 400)
        form["customer"] = self.customer.pk
        for it in form["items"]:
            it["material"] = self.bolt.pk
        form["po_number"] = "OCR-PO-1"
        self.assertEqual(self.client.patch(f"{API}/ocr/extractions/{ex['id']}/", {"draft_data": form}, format="json").status_code, 200)
        v = self.client.post(f"{API}/ocr/extractions/{ex['id']}/verify/", form, format="json")
        self.assertEqual(v.status_code, 200, v.content)
        self.assertEqual(v.json()["status"], "verified")
        po = self.client.post(f"{API}/ocr/extractions/{ex['id']}/create-po/")
        self.assertEqual(po.status_code, 201, po.content)
        po = po.json()
        self.assertEqual(po["source"], "email")
        self.assertTrue(po["attachment_url"])
        refreshed = self.client.get(f"{API}/inbox/messages/{msg['id']}/").json()
        self.assertEqual((refreshed["status"], refreshed["converted_po"]), ("converted", po["id"]))
        self.assertEqual(self.client.post(f"{API}/ocr/extractions/{ex['id']}/create-po/").status_code, 409)  # no double conversion
        self.assertEqual(self.client.delete(f"{API}/purchase-orders/{po['id']}/").status_code, 204)
        self.assertEqual(self.client.get(f"{API}/inbox/messages/{msg['id']}/").json()["status"], "scanned")

    def test_mark_duplicate_rejected_restore(self):
        msg = self.client.post(API + "/inbox/messages/simulate/").json()
        r = self.client.post(f"{API}/inbox/messages/{msg['id']}/mark/", {"status": "duplicate", "note": "same as earlier"}, format="json")
        self.assertEqual(r.json()["status"], "duplicate")
        self.assertEqual(self.client.post(f"{API}/inbox/messages/{msg['id']}/scan/").status_code, 409)
        self.assertEqual(self.client.post(f"{API}/inbox/messages/{msg['id']}/mark/", {"status": "restore"}, format="json").json()["status"], "new")
        self.assertEqual(self.client.post(f"{API}/inbox/messages/{msg['id']}/mark/", {"status": "bogus"}, format="json").status_code, 400)


class UploadOCRTests(BaseAPITest):
    def upload(self, name, data, ctype="application/pdf"):
        return self.client.post(API + "/ocr/extractions/upload/", {"file": SimpleUploadedFile(name, data, content_type=ctype)}, format="multipart")

    def test_real_pdf_text_extraction(self):
        r = self.upload("po.pdf", demo_documents.make_pdf(PO_LINES))
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual((body["status"], body["engine"]), ("processed", "pdf-text"))
        self.assertEqual(body["extracted_data"]["header"]["po_number"]["value"], "APX/9/001")
        self.assertEqual(len(body["extracted_data"]["items"]), 2)

    def test_unsupported_and_corrupt_files(self):
        self.assertEqual(self.upload("notes.txt", b"hello", "text/plain").status_code, 400)
        r = self.upload("broken.pdf", b"this is not really a pdf")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["status"], "failed")
        self.assertIn("PDF", r.json()["error_message"])
        self.assertEqual(self.upload("fake.png", b"not an image", "image/png").json()["status"], "failed")

    def test_image_ocr_with_tesseract(self):
        if not tesseract_info()["available"]:
            self.skipTest("Tesseract is not installed")
        r = self.upload("scan.png", demo_documents.make_png(PO_LINES), "image/png")
        self.assertEqual(r.status_code, 201, r.content)
        body = r.json()
        self.assertEqual(body["engine"], "tesseract")
        self.assertEqual(body["status"], "processed", body["error_message"])
        self.assertIn("4,650", body["raw_text"].replace(" ", ""))
        self.assertTrue(body["extracted_data"]["header"]["po_number"]["value"].startswith("APX"))
