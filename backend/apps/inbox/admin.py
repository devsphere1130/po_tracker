from django.contrib import admin

from .models import InboxAttachment, InboxConnection, InboxMessage


class AttachmentInline(admin.TabularInline):
    model = InboxAttachment
    extra = 0


@admin.register(InboxMessage)
class InboxMessageAdmin(admin.ModelAdmin):
    list_display = ("subject", "sender_email", "received_at", "status", "is_demo")
    list_filter = ("status", "is_demo", "provider")
    inlines = [AttachmentInline]


admin.site.register(InboxConnection)
