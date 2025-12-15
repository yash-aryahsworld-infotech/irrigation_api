import requests
from pydantic import BaseModel, Field
from typing import Optional

# --- CONFIGURATION (Use your OpenWeatherMap Key) ---
OPENWEATHER_API_KEY = "d7450375592754b59457b522cfd4d97c" # Replace with your key
# Base URL for current weather data using Lat/Lon
WEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5/weather" 

# --- Data Models ---
class weatherForecast(BaseModel):
    """Structured output for the weather forecast tool."""
    location: str
    description: str
    tempreture_in_celcius: float

class IrrigationRequirement(BaseModel):
    """Structured output for the irrigation calculation tool."""
    field_size_sq_meter: float
    required_water_liters: float
    reasoning: str

# --- Helper Functions (Tools) ---

def get_weather_forecast_by_coords(lat: float, lon: float) -> weatherForecast:
    """Retrieves weather data from OpenWeatherMap using Latitude and Longitude."""
    params = {
        'lat': lat,
        'lon': lon,
        'appid': OPENWEATHER_API_KEY,
        'units': 'metric'
    }
    
    try:
        response = requests.get(WEATHER_BASE_URL, params=params)
        response.raise_for_status()
        result = response.json()
    except requests.exceptions.RequestException as e:
        return weatherForecast(
            location=f"Lat {lat}, Lon {lon}",
            description=f"Error retrieving weather: {e}",
            tempreture_in_celcius=0.0
        )
    
    # OpenWeatherMap returns the city name in the 'name' field
    location_name = result.get("name", f"Lat {lat:.2f}, Lon {lon:.2f}")
    
    return weatherForecast(
        location=location_name,
        description=result["weather"][0]["description"].capitalize(),
        tempreture_in_celcius=result["main"]["temp"],
    )

def calculate_irrigation_needs(
    weather: weatherForecast, 
    field_size_sq_meter: float
) -> IrrigationRequirement:
    """Calculates water requirement based on weather and field size (same logic)."""
    
    baseline_requirement_L_per_sqm = 5.0
    temp_factor = 1.0 + max(0, weather.tempreture_in_celcius - 20) * 0.05
    is_rainy = "rain" in weather.description.lower() or "shower" in weather.description.lower()
    rain_reduction_factor = 0.6 if is_rainy else 1.0

    adjusted_requirement_L_per_sqm = baseline_requirement_L_per_sqm * temp_factor * rain_reduction_factor
    required_water_liters = adjusted_requirement_L_per_sqm * field_size_sq_meter
    
    reasoning = (
        f"Weather: {weather.description} at {weather.tempreture_in_celcius:.1f}°C. "
        f"Baseline water (5.0 L/m²) was adjusted for high temperature "
        f"({temp_factor:.2f}x) and {'rain' if is_rainy else 'dry conditions'} "
        f"({rain_reduction_factor:.2f}x). "
        f"The final calculated need is {adjusted_requirement_L_per_sqm:.2f} L/m²."
    )
    
    return IrrigationRequirement(
        field_size_sq_meter=field_size_sq_meter,
        required_water_liters=required_water_liters,
        reasoning=reasoning
    )
    
# --- Django-friendly Main Predictor Function ---

def get_irrigation_prediction(lat: float, lon: float, field_size: float) -> dict:
    """The main function called by the Django view."""
    
    # Step 1: Get Weather using Coords
    weather = get_weather_forecast_by_coords(lat, lon)
    
    # Step 2: Calculate Irrigation
    irrigation_data = calculate_irrigation_needs(weather, field_size)
    
    return {
        'weather_location': weather.location,
        'weather_description': weather.description,
        'weather_temp': f"{weather.tempreture_in_celcius:.1f}°C",
        'field_size': f"{irrigation_data.field_size_sq_meter:,.2f}",
        'required_water': f"{irrigation_data.required_water_liters:,.2f} Liters",
        'reasoning': irrigation_data.reasoning
    }