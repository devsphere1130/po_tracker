from rest_framework.routers import DefaultRouter

from .views import SupplyEntryViewSet

router = DefaultRouter()
router.register("", SupplyEntryViewSet, basename="supplyentry")
urlpatterns = router.urls
