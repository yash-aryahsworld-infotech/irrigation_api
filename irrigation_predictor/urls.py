from django.urls import path
from irrigation_predictor.views import (
    HealthCheckAPIView,
    IrrigationPredictionAPIView,
)

urlpatterns = [
    # API endpoint: POST data to /api/predict/
    path("", HealthCheckAPIView.as_view(), name="health-check"),
    path('api/predict/', IrrigationPredictionAPIView.as_view(), name='irrigation_predict_api'),
]