"""Encrypts mailbox refresh tokens at rest (Fernet key derived from DJANGO_SECRET_KEY)."""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt(text):
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token):
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored mailbox token cannot be decrypted (SECRET_KEY changed?). Reconnect the mailbox.") from exc
