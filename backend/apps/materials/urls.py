from rest_framework.routers import DefaultRouter

from .views import MaterialAliasViewSet, MaterialViewSet

router = DefaultRouter()
router.register("aliases", MaterialAliasViewSet, basename="materialalias")
router.register("", MaterialViewSet, basename="material")
urlpatterns = router.urls
