from rest_framework import serializers

from .models import Material, MaterialAlias


class MaterialSerializer(serializers.ModelSerializer):
    uom_display = serializers.CharField(source="get_uom_display", read_only=True)
    usage_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Material
        fields = [
            "id", "material_code", "name", "description", "category", "uom", "uom_display",
            "default_rate", "is_active", "usage_count", "created_at", "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]
        extra_kwargs = {"material_code": {"validators": []}}

    def _others(self):
        qs = Material.objects.all()
        return qs.exclude(pk=self.instance.pk) if self.instance else qs

    def validate_material_code(self, v):
        v = v.strip().upper()
        if self._others().filter(material_code__iexact=v).exists():
            raise serializers.ValidationError("A material with this code already exists.")
        return v

    def validate_name(self, v):
        v = " ".join(v.split())
        if self._others().filter(name__iexact=v).exists():
            raise serializers.ValidationError("A material with this name already exists.")
        return v

    def validate_default_rate(self, v):
        if v < 0:
            raise serializers.ValidationError("Default rate cannot be negative.")
        return v


class MaterialAliasSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source="material.name", read_only=True)

    class Meta:
        model = MaterialAlias
        fields = ["id", "material", "material_name", "description", "created_at"]
        read_only_fields = ["created_at"]

    def validate_description(self, v):
        norm = MaterialAlias.normalize(v)
        qs = MaterialAlias.objects.filter(normalized=norm)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This description is already mapped to a material.")
        return v.strip()
