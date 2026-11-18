from rest_framework.routers import DefaultRouter

from .views import PurchaseOrderViewSet

router = DefaultRouter()
router.register("", PurchaseOrderViewSet, basename="purchaseorder")
urlpatterns = router.urls
