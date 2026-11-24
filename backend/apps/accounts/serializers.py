from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import AuditLog, CompanyProfile, Profile
from .permissions import user_role

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=Profile.ROLES, required=False)
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "is_active", "role", "phone", "password", "date_joined", "last_login"]
        read_only_fields = ["date_joined", "last_login"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["role"] = user_role(instance)
        data["phone"] = getattr(getattr(instance, "profile", None), "phone", "")
        return data

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "Password is required."})
        return attrs

    def _save_profile(self, user, role, phone):
        profile, _ = Profile.objects.get_or_create(user=user)
        if role:
            profile.role = role
            user.is_staff = role == Profile.ADMIN  # Django admin site access
            user.save(update_fields=["is_staff"])
        if phone is not None:
            profile.phone = phone
        profile.save()

    def create(self, validated):
        role = validated.pop("role", Profile.STAFF)
        phone = validated.pop("phone", "")
        password = validated.pop("password")
        user = User(**validated)
        user.set_password(password)
        user.save()
        self._save_profile(user, role, phone)
        return user

    def update(self, instance, validated):
        role = validated.pop("role", None)
        phone = validated.pop("phone", None)
        password = validated.pop("password", None)
        request = self.context.get("request")
        if request and instance.pk == request.user.pk:
            if role == Profile.STAFF or validated.get("is_active") is False:
                raise serializers.ValidationError("You cannot demote or deactivate your own account.")
        for k, v in validated.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        self._save_profile(instance, role, phone)
        return instance


class CompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyProfile
        fields = ["name", "gst_number", "email", "phone", "address", "updated_at"]
        read_only_fields = ["updated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ["id", "username", "action", "model_name", "object_id", "object_repr", "details", "created_at"]
