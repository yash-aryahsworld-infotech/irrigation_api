# irrigation_predictor/serializers.py

from rest_framework import serializers

class PredictionRequestSerializer(serializers.Serializer):
    """
    Handles validation for incoming request data, supporting lat/lon or city name.
    """
    # Location Input (Optional fields, validated together in the .validate method)
    city = serializers.CharField(
        max_length=100, 
        required=False,
        allow_blank=True,
        help_text="City name for location lookup."
    )
    latitude = serializers.FloatField(
        min_value=-90.0, 
        max_value=90.0, 
        required=False,
        allow_null=True,
        help_text="Geographical latitude (-90 to 90)."
    )
    longitude = serializers.FloatField(
        min_value=-180.0, 
        max_value=180.0, 
        required=False,
        allow_null=True,
        help_text="Geographical longitude (-180 to 180)."
    )
    
    # Required field for prediction
    field_size_sq_meter = serializers.FloatField(
        min_value=0.1, 
        help_text="The size of the crop field in square meters."
    )

    # Custom validation to ensure at least city OR (lat AND lon) are provided
    def validate(self, data):
        city = data.get('city')
        lat = data.get('latitude')
        lon = data.get('longitude')

        has_city = bool(city)
        has_coords = (lat is not None) and (lon is not None)
        
        if not (has_city or has_coords):
            raise serializers.ValidationError(
                "Must provide either 'city' or both 'latitude' and 'longitude'."
            )
        
        if has_city and has_coords:
             raise serializers.ValidationError(
                "Please provide either 'city' OR 'latitude'/'longitude', not both."
            )
            
        return data

class IrrigationResultSerializer(serializers.Serializer):
    """Handles serialization for the complete JSON response."""
    weather_location = serializers.CharField()
    weather_description = serializers.CharField()
    weather_temp = serializers.CharField(help_text="Temperature in Celsius with unit.")
    field_size = serializers.CharField(help_text="Field size with unit (m²).")
    required_water = serializers.CharField(help_text="Total required water in Liters with unit.")
    reasoning = serializers.CharField(help_text="Detailed explanation of the calculation.")
    error = serializers.CharField(required=False, allow_null=True)