import re

from rest_framework import serializers

from .models import Customer

GST_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
MOBILE_RE = re.compile(r"^\+?\d[\d\s-]{8,17}$")


class CustomerSerializer(serializers.ModelSerializer):
    po_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Customer
        fields = [
            "id", "customer_code", "name", "contact_person", "email", "mobile", "gst_number",
            "billing_address", "shipping_address", "is_active", "po_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"customer_code": {"validators": []}}  # custom duplicate message below

    def _others(self):
        qs = Customer.objects.all()
        return qs.exclude(pk=self.instance.pk) if self.instance else qs

    def validate_customer_code(self, v):
        v = v.strip().upper()
        if self._others().filter(customer_code__iexact=v).exists():
            raise serializers.ValidationError("A customer with this code already exists.")
        return v

    def validate_name(self, v):
        v = " ".join(v.split())
        dup = self._others().filter(name__iexact=v).first()
        if dup:
            raise serializers.ValidationError(f"Duplicate customer: '{dup.name}' ({dup.customer_code}) already exists.")
        return v

    def validate_gst_number(self, v):
        v = v.strip().upper()
        if not v:
            return v
        if not GST_RE.match(v):
            raise serializers.ValidationError("Invalid GST number format (expected 15 characters, e.g. 27AABCU9603R1ZM).")
        dup = self._others().filter(gst_number=v).first()
        if dup:
            raise serializers.ValidationError(f"GST number already used by customer '{dup.name}'.")
        return v

    def validate_mobile(self, v):
        v = v.strip()
        if v and not MOBILE_RE.match(v):
            raise serializers.ValidationError("Enter a valid mobile number (9-15 digits).")
        return v
