from rest_framework import serializers
from .models import Country

class CountrySerializer(serializers.ModelSerializer):
    """
    Serializer for Country model.
    
    Handles conversion between Country objects and JSON.
    Also validates incoming data.
    """
    
    class Meta:
        model = Country
        fields = [
            'id',
            'name',
            'capital',
            'region',
            'population',
            'currency_code',
            'exchange_rate',
            'estimated_gdp',
            'flag_url',
            'last_refreshed_at'
        ]
        # Make id read-only (auto-generated)
        read_only_fields = ['id', 'last_refreshed_at']
    
    def validate_name(self, value):
        """Custom validation for name field"""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip()
    
    def validate_population(self, value):
        """Ensure population is positive"""
        if value < 0:
            raise serializers.ValidationError("Population must be positive")
        return value


class CountryFilterSerializer(serializers.Serializer):
    """
    Validates query parameters for filtering.
    
    This isn't tied to a model - just validates incoming filters.
    """
    region = serializers.CharField(required=False, max_length=100)
    currency = serializers.CharField(required=False, max_length=10)
    sort = serializers.ChoiceField(
        choices=['gdp_asc', 'gdp_desc', 'population_asc', 'population_desc', 'name_asc', 'name_desc'],
        required=False
    )