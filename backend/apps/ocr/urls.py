from rest_framework.routers import DefaultRouter

from .views import OCRExtractionViewSet

router = DefaultRouter()
router.register("extractions", OCRExtractionViewSet, basename="ocrextraction")
urlpatterns = router.urls
