from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.db import connection


def health(request):
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        db = "ok"
    except Exception:  # pragma: no cover
        db = "error"
    return JsonResponse({"status": "ok" if db == "ok" else "degraded", "database": db})


api_v1 = [
    path("health/", health),
    path("auth/", include("apps.accounts.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("customers/", include("apps.customers.urls")),
    path("materials/", include("apps.materials.urls")),
    path("inbox/", include("apps.inbox.urls")),
    path("ocr/", include("apps.ocr.urls")),
    path("purchase-orders/", include("apps.purchase_orders.urls")),
    path("supply-entries/", include("apps.supply_tracking.urls")),
    path("reports/", include("apps.reports.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
]
