# irrigation_predictor/views.py

import os
import requests
from pydantic import BaseModel
from typing import Optional
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import PredictionRequestSerializer, IrrigationResultSerializer


# --- 1. CORE LOGIC & MODELS (Integrated for easy deployment) ---

# Replace with your actual key
OPENWEATHER_API_KEY = "d7450375592754b59457b522cfd4d97c" 
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
GEOCODING_BASE_URL = "http://api.openweathermap.org/geo/1.0/direct"

class weatherForecast(BaseModel):
    location: str
    description: str
    tempreture_in_celcius: float

class IrrigationRequirement(BaseModel):
    field_size_sq_meter: float
    required_water_liters: float
    reasoning: str

# Helper 1: Geocoding Function (City -> Lat/Lon)
def get_coords_from_city(city: str) -> Optional[tuple[float, float]]:
    """Converts a city name to (latitude, longitude) using Geocoding API."""
    params = { 'q': city, 'limit': 1, 'appid': OPENWEATHER_API_KEY }
    try:
        response = requests.get(GEOCODING_BASE_URL, params=params)
        response.raise_for_status()
        result = response.json()
        if result and len(result) > 0:
            return (result[0]['lat'], result[0]['lon'])
        else:
            return None
    except requests.exceptions.RequestException:
        return None

# Helper 2: Weather Retrieval Function
def get_weather_forecast_by_coords(lat: float, lon: float) -> weatherForecast:
    """Retrieves weather data from OpenWeatherMap using Lat/Lon."""
    params = { 'lat': lat, 'lon': lon, 'appid': OPENWEATHER_API_KEY, 'units': 'metric' }
    try:
        response = requests.get(WEATHER_BASE_URL, params=params)
        response.raise_for_status()
        result = response.json()
        location_name = result.get("name", f"Lat {lat:.2f}, Lon {lon:.2f}")
        return weatherForecast(
            location=location_name,
            description=result["weather"][0]["description"].capitalize(),
            tempreture_in_celcius=result["main"]["temp"],
        )
    except requests.exceptions.RequestException as e:
        return weatherForecast(
            location=f"Lat {lat}, Lon {lon}",
            description=f"Error retrieving weather: {e}",
            tempreture_in_celcius=0.0
        )

# Helper 3: Irrigation Calculation Function (Simplified)
def calculate_irrigation_needs(
    weather: weatherForecast, 
    field_size_sq_meter: float
) -> IrrigationRequirement:
    """Calculates water requirement based on weather and field size."""
    
    baseline_requirement_L_per_sqm = 5.0
    temp_factor = 1.0 + max(0, weather.tempreture_in_celcius - 20) * 0.05
    is_rainy = "rain" in weather.description.lower() or "shower" in weather.description.lower()
    rain_reduction_factor = 0.6 if is_rainy else 1.0

    adjusted_requirement_L_per_sqm = baseline_requirement_L_per_sqm * temp_factor * rain_reduction_factor
    required_water_liters = adjusted_requirement_L_per_sqm * field_size_sq_meter
    
    reasoning = (
        f"Weather: {weather.description} at {weather.tempreture_in_celcius:.1f}°C. "
        f"Baseline (5.0 L/m²) adjusted for temp ({temp_factor:.2f}x) and rain ({rain_reduction_factor:.2f}x). "
        f"Final need is {adjusted_requirement_L_per_sqm:.2f} L/m²."
    )
    
    return IrrigationRequirement(
        field_size_sq_meter=field_size_sq_meter,
        required_water_liters=required_water_liters,
        reasoning=reasoning
    )

# Main Predictor Function
def get_irrigation_prediction(city: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None, field_size: float = 0.0) -> dict:
    
    # 1. Determine Coordinates (Geocoding if needed)
    if city:
        coords = get_coords_from_city(city)
        if coords:
            lat, lon = coords
        else:
            return {'error': f"City '{city}' not found or geocoding failed.", 'weather_location': city}
    
    if lat is None or lon is None:
        return {'error': "Location (city or coordinates) must be provided."}

    # 2. Get Weather
    weather = get_weather_forecast_by_coords(lat, lon)
    
    # 3. Calculate Irrigation
    irrigation_data = calculate_irrigation_needs(weather, field_size)
    
    return {
        'weather_location': weather.location,
        'weather_description': weather.description,
        'weather_temp': f"{weather.tempreture_in_celcius:.1f}°C",
        'field_size': f"{irrigation_data.field_size_sq_meter:,.2f}",
        'required_water': f"{irrigation_data.required_water_liters:,.2f} Liters",
        'reasoning': irrigation_data.reasoning
    }

# --- 2. API VIEW ---

class IrrigationPredictionAPIView(APIView):
    """
    API endpoint accepting either city name or lat/lon coordinates.
    """
    def post(self, request, *args, **kwargs):
        # 1. Validate Incoming Data using the flexible serializer
        request_serializer = PredictionRequestSerializer(data=request.data)
        
        if not request_serializer.is_valid():
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract validated data
        city = request_serializer.validated_data.get('city')
        lat = request_serializer.validated_data.get('latitude')
        lon = request_serializer.validated_data.get('longitude')
        field_size = request_serializer.validated_data['field_size_sq_meter']
        
        try:
            # 2. Call the core logic function
            prediction_data = get_irrigation_prediction(
                city=city,
                lat=lat,
                lon=lon,
                field_size=field_size
            )
            
            # 3. Check for logic errors (e.g., city not found)
            if 'error' in prediction_data:
                 return Response(prediction_data, status=status.HTTP_404_NOT_FOUND)

            # 4. Serialize and Return Outgoing Data
            result_serializer = IrrigationResultSerializer(data=prediction_data)
            result_serializer.is_valid(raise_exception=True) 
            
            return Response(result_serializer.data, status=status.HTTP_200_OK)
            
        except Exception as e:
            # Handle unexpected Python exceptions
            error_response = {
                "error": "An unexpected server error occurred during prediction.",
                "details": str(e)
            }
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)