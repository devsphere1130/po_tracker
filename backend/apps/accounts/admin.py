from django.contrib import admin

from .models import AuditLog, CompanyProfile, Profile

admin.site.register(Profile)
admin.site.register(CompanyProfile)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "model_name", "object_repr")
    list_filter = ("action", "model_name")
