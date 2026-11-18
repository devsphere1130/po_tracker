from .models import AuditLog


def log_action(user, action, instance=None, model_name=None, details=None):
    if user is not None and not getattr(user, "is_authenticated", False):
        user = None
    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name or (instance.__class__.__name__ if instance is not None else ""),
        object_id=str(getattr(instance, "pk", "") or ""),
        object_repr=str(instance)[:255] if instance is not None else "",
        details=details or {},
    )


class AuditMixin:
    """Writes AuditLog rows for create/update/delete in DRF viewsets."""

    def perform_create(self, serializer):
        obj = serializer.save()
        log_action(self.request.user, "create", obj)

    def perform_update(self, serializer):
        obj = serializer.save()
        log_action(self.request.user, "update", obj, details={"fields": list(serializer.validated_data.keys())})

    def perform_destroy(self, instance):
        log_action(self.request.user, "delete", instance)
        instance.delete()
