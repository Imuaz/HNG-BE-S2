from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import FileResponse, Http404
from django.db.models import Q
from .models import Country
from .serializers import CountrySerializer, CountryFilterSerializer
from .services import CountryService, ExternalAPIError
from .utils import ImageGenerator
import os


@api_view(['POST'])
def refresh_countries(request):
    """
    POST /countries/refresh
    
    Fetches all countries and exchange rates, then caches them in database.
    Also generates summary image.
    """
    try:
        # Refresh data
        result = CountryService.refresh_countries()
        
        # Generate image
        try:
            ImageGenerator.generate_summary_image()
        except Exception as e:
            # Log error but don't fail the request
            print(f"Image generation failed: {e}")
        
        return Response({
            'message': 'Countries refreshed successfully',
            'total_countries': result['total_countries'],
            'created': result['created'],
            'updated': result['updated'],
            'last_refreshed_at': result['last_refreshed_at']
        }, status=status.HTTP_200_OK)
    
    except ExternalAPIError as e:
        return Response({
            'error': 'External data source unavailable',
            'details': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    except Exception as e:
        return Response({
            'error': 'Internal server error',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def list_countries(request):
    """
    GET /countries
    
    Get all countries with optional filtering and sorting.
    
    Query parameters:
    - region: Filter by region (e.g., ?region=Africa)
    - currency: Filter by currency code (e.g., ?currency=NGN)
    - sort: Sort results (e.g., ?sort=gdp_desc)
    """
    # Validate query parameters
    filter_serializer = CountryFilterSerializer(data=request.query_params)
    if not filter_serializer.is_valid():
        return Response({
            'error': 'Invalid query parameters',
            'details': filter_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Start with all countries
    queryset = Country.objects.all()
    
    # Apply filters
    validated_data = filter_serializer.validated_data
    
    if 'region' in validated_data:
        queryset = queryset.filter(region__iexact=validated_data['region'])
    
    if 'currency' in validated_data:
        queryset = queryset.filter(currency_code__iexact=validated_data['currency'])
    
    # Apply sorting
    if 'sort' in validated_data:
        sort_param = validated_data['sort']
        sort_mapping = {
            'gdp_asc': 'estimated_gdp',
            'gdp_desc': '-estimated_gdp',
            'population_asc': 'population',
            'population_desc': '-population',
            'name_asc': 'name',
            'name_desc': '-name'
        }
        queryset = queryset.order_by(sort_mapping[sort_param])
    
    # Serialize and return
    serializer = CountrySerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_country(request, name):
    """
    GET /countries/:name
    
    Get a single country by name (case-insensitive).
    """
    try:
        country = Country.objects.get(name__iexact=name)
        serializer = CountrySerializer(country)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Country.DoesNotExist:
        return Response({
            'error': 'Country not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
def delete_country(request, name):
    """
    DELETE /countries/:name
    
    Delete a country by name (case-insensitive).
    """
    try:
        country = Country.objects.get(name__iexact=name)
        country.delete()
        return Response({
            'message': f'Country "{name}" deleted successfully'
        }, status=status.HTTP_200_OK)
    except Country.DoesNotExist:
        return Response({
            'error': 'Country not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_status(request):
    """
    GET /status
    
    Show total countries and last refresh timestamp.
    """
    total_countries = Country.objects.count()
    
    # Get the most recent refresh time
    latest_country = Country.objects.order_by('-last_refreshed_at').first()
    last_refreshed = latest_country.last_refreshed_at if latest_country else None
    
    return Response({
        'total_countries': total_countries,
        'last_refreshed_at': last_refreshed
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_summary_image(request):
    """
    GET /countries/image
    
    Serve the generated summary image.
    """
    image_path = ImageGenerator.get_image_path()
    
    if not os.path.exists(image_path):
        return Response({
            'error': 'Summary image not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return FileResponse(open(image_path, 'rb'), content_type='image/png')