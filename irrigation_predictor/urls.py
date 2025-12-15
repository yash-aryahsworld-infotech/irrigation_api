from django.urls import path
from .views import IrrigationPredictionAPIView

urlpatterns = [
    # API endpoint: POST data to /api/predict/
    path('api/predict/', IrrigationPredictionAPIView.as_view(), name='irrigation_predict_api'),
]