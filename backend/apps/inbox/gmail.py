"""Gmail API client (OAuth 2.0 web flow, read-only scope). Uses plain HTTPS calls via requests."""
import base64
from datetime import datetime, timezone
from email.utils import parseaddr
from urllib.parse import urlencode

import requests
from django.conf import settings

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
API = "https://gmail.googleapis.com/gmail/v1/users/me"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
SUPPORTED_EXT = (".pdf", ".png", ".jpg", ".jpeg")
CONTENT_TYPES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
SEARCH_QUERY = "has:attachment in:inbox newer_than:30d"


class GmailError(Exception):
    pass


class GmailAuthError(GmailError):
    """Refresh token revoked/expired: the user must reconnect."""


def _http(method, url, **kw):
    kw.setdefault("timeout", 30)
    try:
        resp = requests.request(method, url, **kw)
    except requests.RequestException as exc:
        raise GmailError(f"Could not reach Google: {exc}") from exc
    if resp.status_code >= 400:
        try:
            body = resp.json()
        except ValueError:
            body = {}
        err = body.get("error")
        code = err if isinstance(err, str) else (err or {}).get("status", "")
        message = body.get("error_description") or (err.get("message") if isinstance(err, dict) else err) or resp.text[:200]
        if code == "invalid_grant" or resp.status_code == 401:
            raise GmailAuthError(str(message))
        raise GmailError(f"Google API error {resp.status_code}: {message}")
    return resp.json()


def build_auth_url(state):
    params = {
        "client_id": settings.GMAIL_CLIENT_ID, "redirect_uri": settings.GMAIL_REDIRECT_URI, "response_type": "code",
        "scope": SCOPE, "access_type": "offline", "prompt": "consent", "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def exchange_code(code):
    return _http("POST", TOKEN_URL, data={
        "code": code, "client_id": settings.GMAIL_CLIENT_ID, "client_secret": settings.GMAIL_CLIENT_SECRET,
        "redirect_uri": settings.GMAIL_REDIRECT_URI, "grant_type": "authorization_code",
    })


def refresh_access_token(refresh_token):
    data = _http("POST", TOKEN_URL, data={
        "refresh_token": refresh_token, "client_id": settings.GMAIL_CLIENT_ID,
        "client_secret": settings.GMAIL_CLIENT_SECRET, "grant_type": "refresh_token",
    })
    return data["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def get_profile(token):
    return _http("GET", f"{API}/profile", headers=_auth(token))


def list_message_ids(token, page_token=None, max_results=50):
    params = {"q": SEARCH_QUERY, "maxResults": max_results}
    if page_token:
        params["pageToken"] = page_token
    data = _http("GET", f"{API}/messages", headers=_auth(token), params=params)
    return [m["id"] for m in data.get("messages", [])], data.get("nextPageToken")


def get_message(token, message_id):
    return _http("GET", f"{API}/messages/{message_id}", headers=_auth(token), params={"format": "full"})


def get_attachment(token, message_id, attachment_id):
    data = _http("GET", f"{API}/messages/{message_id}/attachments/{attachment_id}", headers=_auth(token))
    return _b64(data.get("data", ""))


def _b64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)) if s else b""


def _walk(part):
    yield part
    for child in part.get("parts", []) or []:
        yield from _walk(child)


def parse_message(msg, token):
    """Convert a Gmail 'full' message into a plain dict. Only PDF/PNG/JPG attachments are kept."""
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", [])}
    name, email = parseaddr(headers.get("from", ""))
    body, attachments = "", []
    for part in _walk(payload):
        filename = part.get("filename") or ""
        data = part.get("body", {})
        if filename:
            ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in SUPPORTED_EXT or int(data.get("size", 0)) > settings.MAX_UPLOAD_BYTES:
                continue
            content = _b64(data["data"]) if data.get("data") else get_attachment(token, msg["id"], data["attachmentId"]) if data.get("attachmentId") else b""
            if content:
                attachments.append({"external_id": f"part-{part.get('partId', len(attachments))}", "filename": filename[:300],
                                    "content_type": CONTENT_TYPES[ext], "content": content})
        elif part.get("mimeType") == "text/plain" and data.get("data") and not body:
            body = _b64(data["data"]).decode("utf-8", "replace")[:5000]
    received = datetime.fromtimestamp(int(msg.get("internalDate", 0)) / 1000, tz=timezone.utc)
    return {
        "external_id": msg["id"], "sender_name": name[:200], "sender_email": email or "unknown@invalid",
        "subject": (headers.get("subject") or "(no subject)")[:400], "body": body, "received_at": received,
        "attachments": attachments,
    }
