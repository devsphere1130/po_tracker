from decimal import Decimal

from django.db import models
from django.db.models.functions import Lower

UOM_CHOICES = [
    ("NOS", "Nos"), ("PCS", "Pcs"), ("KG", "Kg"), ("MTR", "Mtr"), ("LTR", "Ltr"),
    ("BOX", "Box"), ("SET", "Set"), ("TON", "Ton"), ("ROLL", "Roll"), ("BAG", "Bag"),
]


class Material(models.Model):
    material_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=80, blank=True)
    uom = models.CharField("Unit of measurement", max_length=10, choices=UOM_CHOICES, default="NOS")
    default_rate = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(Lower("name"), name="uniq_material_name_ci")]
        indexes = [models.Index(fields=["category"]), models.Index(fields=["is_active"])]

    def __str__(self):
        return f"{self.material_code} - {self.name}"


class MaterialAlias(models.Model):
    """Maps a customer/OCR-provided description to a master material."""

    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="aliases")
    description = models.CharField(max_length=300)
    normalized = models.CharField(max_length=300, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["description"]

    @staticmethod
    def normalize(text):
        return " ".join((text or "").lower().split())

    def save(self, *args, **kwargs):
        self.normalized = self.normalize(self.description)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} -> {self.material.material_code}"
