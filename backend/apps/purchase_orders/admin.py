from django.contrib import admin

from .models import PurchaseOrder, PurchaseOrderItem


class ItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ("supplied_quantity", "line_amount")


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("po_number", "customer", "po_date", "delivery_date", "status", "order_total", "source")
    list_filter = ("status", "source")
    search_fields = ("po_number", "customer__name")
    inlines = [ItemInline]
    readonly_fields = ("order_total",)
