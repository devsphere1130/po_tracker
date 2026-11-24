from django.contrib import admin

from .models import Material, MaterialAlias


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("material_code", "name", "category", "uom", "default_rate", "is_active")
    search_fields = ("material_code", "name")
    list_filter = ("is_active", "category", "uom")


admin.site.register(MaterialAlias)
