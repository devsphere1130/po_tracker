from django.conf import settings
from django.db import models


class Profile(models.Model):
    ADMIN = "admin"
    STAFF = "staff"
    ROLES = [(ADMIN, "Admin"), (STAFF, "Staff")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLES, default=STAFF)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class CompanyProfile(models.Model):
    """Singleton: the supplier's own company details."""

    name = models.CharField(max_length=200, default="My Supplier Company")
    gst_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.name


class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=30)  # create/update/delete/login/...
    model_name = models.CharField(max_length=60)
    object_id = models.CharField(max_length=40, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["model_name", "object_id"]), models.Index(fields=["-created_at"])]

    def __str__(self):
        return f"{self.action} {self.model_name} {self.object_id}"
