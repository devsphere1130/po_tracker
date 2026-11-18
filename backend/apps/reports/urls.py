from django.urls import path

from .views import ReportView

urlpatterns = [
    path("po-status/<str:kind>/", ReportView.as_view(), {"name": "po-status"}),
    path("<str:name>/", ReportView.as_view()),
]
