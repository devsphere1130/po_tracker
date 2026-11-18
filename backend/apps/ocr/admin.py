from django.contrib import admin

from .models import OCRExtraction


@admin.register(OCRExtraction)
class OCRExtractionAdmin(admin.ModelAdmin):
    list_display = ("id", "original_filename", "status", "engine", "linked_po", "created_at")
    list_filter = ("status", "engine")
