from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("audit-logs", views.AuditLogViewSet, basename="auditlog")

urlpatterns = [
    path("csrf/", views.csrf),
    path("login/", views.login_view),
    path("logout/", views.logout_view),
    path("me/", views.me_view),
    path("company/", views.CompanyProfileView.as_view()),
    path("", include(router.urls)),
]
