from django.contrib import admin

from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("customer_code", "name", "contact_person", "email", "gst_number", "is_active")
    search_fields = ("customer_code", "name", "gst_number")
    list_filter = ("is_active",)
