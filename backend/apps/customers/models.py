from django.db import models
from django.db.models.functions import Lower


class Customer(models.Model):
    customer_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    mobile = models.CharField(max_length=20, blank=True)
    gst_number = models.CharField(max_length=15, blank=True)
    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(Lower("name"), name="uniq_customer_name_ci"),
            models.UniqueConstraint(
                fields=["gst_number"], condition=~models.Q(gst_number=""), name="uniq_customer_gst_nonblank"
            ),
        ]
        indexes = [models.Index(fields=["is_active"]), models.Index(fields=["name"])]

    def __str__(self):
        return f"{self.customer_code} - {self.name}"
