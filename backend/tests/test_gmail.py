import base64
from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.test import override_settings

from apps.inbox import demo_documents, gmail
from apps.inbox.models import InboxConnection, InboxMessage
from apps.inbox.views import ensure_connections

from .base import API, BaseAPITest

LIVE = dict(INBOX_MODE="live", GMAIL_CLIENT_ID="cid.apps.googleusercontent.com", GMAIL_CLIENT_SECRET="sec",
            FRONTEND_URL="http://localhost:5173")


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


PDF = demo_documents.make_pdf(["PO Number: G-1", "Buyer: Apex Engineering Works Pvt Ltd"])


def message(mid, with_pdf=True):
    parts = [{"partId": "0", "mimeType": "text/plain", "filename": "", "body": {"data": b64(b"Please find PO")}}]
    if with_pdf:
        parts.append({"partId": "1", "mimeType": "application/pdf", "filename": "po.pdf", "body": {"size": len(PDF), "attachmentId": "ATT1"}})
    parts.append({"partId": "2", "mimeType": "image/gif", "filename": "logo.gif", "body": {"size": 10, "attachmentId": "ATT2"}})
    return {"id": mid, "internalDate": "1763000000000", "payload": {
        "headers": [{"name": "From", "value": "Rahul <purchase@apexengg.example>"}, {"name": "Subject", "value": f"PO {mid}"}],
        "parts": parts}}


class FakeGoogle:
    def __init__(self, refresh_error=None):
        self.refresh_error = refresh_error
        self.calls = []

    def __call__(self, method, url, **kw):
        self.calls.append(url)
        if url == gmail.TOKEN_URL:
            if kw["data"]["grant_type"] == "authorization_code":
                return {"access_token": "ACCESS", "refresh_token": "REFRESH-SECRET"}
            if self.refresh_error:
                raise self.refresh_error
            return {"access_token": "ACCESS"}
        if url.endswith("/profile"):
            return {"emailAddress": "orders@example.com"}
        if url.endswith("/messages"):
            return {"messages": [{"id": "m1"}, {"id": "m2"}]}
        if url.endswith("/messages/m1"):
            return message("m1")
        if url.endswith("/messages/m2"):
            return message("m2", with_pdf=False)
        if url.endswith("/attachments/ATT1"):
            return {"data": b64(PDF)}
        raise AssertionError(f"unexpected call {url}")


@override_settings(**LIVE)
class GmailFlowTests(BaseAPITest):
    def gmail_conn(self):
        ensure_connections()
        return InboxConnection.objects.get(provider="gmail")

    def connect_via_callback(self, fake):
        conn = self.gmail_conn()
        url = self.client.post(f"{API}/inbox/connections/{conn.pk}/connect/").json()["authorization_url"]
        state = parse_qs(urlparse(url).query)["state"][0]
        with mock.patch.object(gmail, "_http", fake):
            return self.client.get(f"{API}/inbox/oauth/gmail/callback/?code=abc&state={state}")

    def test_connect_returns_google_url_with_readonly_scope(self):
        conn = self.gmail_conn()
        r = self.client.post(f"{API}/inbox/connections/{conn.pk}/connect/")
        self.assertEqual(r.status_code, 200)
        q = parse_qs(urlparse(r.json()["authorization_url"]).query)
        self.assertEqual(q["scope"], [gmail.SCOPE])
        self.assertEqual(q["access_type"], ["offline"])
        conn.refresh_from_db()
        self.assertEqual(conn.state, "disconnected")  # not connected merely by clicking Connect

    @override_settings(GMAIL_CLIENT_ID="", GMAIL_CLIENT_SECRET="")
    def test_connect_refused_without_credentials(self):
        conn = self.gmail_conn()
        self.assertEqual(self.client.post(f"{API}/inbox/connections/{conn.pk}/connect/").status_code, 409)

    def test_callback_rejects_bad_state(self):
        conn = self.gmail_conn()
        self.client.post(f"{API}/inbox/connections/{conn.pk}/connect/")
        r = self.client.get(f"{API}/inbox/oauth/gmail/callback/?code=abc&state=forged")
        self.assertIn("gmail=error", r["Location"])
        conn.refresh_from_db()
        self.assertEqual(conn.state, "disconnected")

    def test_callback_connects_and_encrypts_token(self):
        r = self.connect_via_callback(FakeGoogle())
        self.assertIn("gmail=connected", r["Location"])
        conn = self.gmail_conn()
        self.assertEqual((conn.state, conn.account_email), ("connected", "orders@example.com"))
        self.assertTrue(conn.token_encrypted)
        self.assertNotIn("REFRESH-SECRET", conn.token_encrypted)
        listing = self.client.get(f"{API}/inbox/connections/").text
        self.assertNotIn(conn.token_encrypted, listing)

    def test_live_sync_imports_only_pdf_emails_once(self):
        self.connect_via_callback(FakeGoogle())
        fake = FakeGoogle()
        with mock.patch.object(gmail, "_http", fake):
            first = self.client.post(f"{API}/inbox/messages/sync/", {}, format="json")
            second = self.client.post(f"{API}/inbox/messages/sync/", {}, format="json")
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(first.json()["imported"], 1)  # m2 has no supported attachment; logo.gif ignored
        self.assertEqual(second.json()["imported"], 0)
        msg = InboxMessage.objects.get()
        self.assertEqual((msg.provider, msg.is_demo, msg.sender_email), ("gmail", False, "purchase@apexengg.example"))
        self.assertEqual([a.filename for a in msg.attachments.all()], ["po.pdf"])
        self.assertEqual(msg.attachments.first().file.read(), PDF)

    def test_revoked_token_disconnects(self):
        self.connect_via_callback(FakeGoogle())
        fake = FakeGoogle(refresh_error=gmail.GmailAuthError("revoked"))
        with mock.patch.object(gmail, "_http", fake):
            r = self.client.post(f"{API}/inbox/messages/sync/", {}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.gmail_conn().state, "disconnected")

    def test_sync_without_connection_refused_and_disconnect(self):
        self.assertEqual(self.client.post(f"{API}/inbox/messages/sync/", {}, format="json").status_code, 409)
        self.connect_via_callback(FakeGoogle())
        conn = self.gmail_conn()
        self.assertEqual(self.client.post(f"{API}/inbox/connections/{conn.pk}/disconnect/").json()["state"], "disconnected")
        conn.refresh_from_db()
        self.assertEqual(conn.token_encrypted, "")
