from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import InboxConnectionViewSet, InboxMessageViewSet, attachment_file

router = DefaultRouter()
router.register("messages", InboxMessageViewSet, basename="inboxmessage")
router.register("connections", InboxConnectionViewSet, basename="inboxconnection")
urlpatterns = [path("attachments/<int:pk>/file/", attachment_file)] + router.urls
