from django.contrib import admin

from .models import SupplyEntry


@admin.register(SupplyEntry)
class SupplyEntryAdmin(admin.ModelAdmin):
    list_display = ("po", "item", "supply_date", "quantity", "challan_number")
    list_filter = ("supply_date",)
    search_fields = ("po__po_number", "challan_number")
