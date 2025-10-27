from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import FileResponse
from django.db.models import F
from .models import Country
from .serializers import CountrySerializer, CountryFilterSerializer
from .services import CountryService, ExternalAPIError
from .utils import ImageGenerator
import os


@api_view(['POST'])
def refresh_countries(request):
    """POST /countries/refresh"""
    try:
        result = CountryService.refresh_countries()
        
        try:
            ImageGenerator.generate_summary_image()
        except Exception as e:
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
    """GET /countries with filters and sorting"""
    filter_serializer = CountryFilterSerializer(data=request.query_params)
    if not filter_serializer.is_valid():
        return Response({
            'error': 'Invalid query parameters',
            'details': filter_serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    queryset = Country.objects.all()
    validated_data = filter_serializer.validated_data
    
    if 'region' in validated_data:
        queryset = queryset.filter(region__iexact=validated_data['region'])
    
    if 'currency' in validated_data:
        queryset = queryset.filter(currency_code__iexact=validated_data['currency'])
    
    # FIX: Handle NULL values in GDP sorting
    if 'sort' in validated_data:
        sort_param = validated_data['sort']
        
        if sort_param == 'gdp_desc':
            queryset = queryset.order_by(F('estimated_gdp').desc(nulls_last=True))
        elif sort_param == 'gdp_asc':
            queryset = queryset.order_by(F('estimated_gdp').asc(nulls_last=True))
        elif sort_param == 'population_desc':
            queryset = queryset.order_by('-population')
        elif sort_param == 'population_asc':
            queryset = queryset.order_by('population')
        elif sort_param == 'name_desc':
            queryset = queryset.order_by('-name')
        elif sort_param == 'name_asc':
            queryset = queryset.order_by('name')
    
    serializer = CountrySerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET', 'DELETE'])
def country_detail(request, name):
    """GET or DELETE /countries/:name"""
    try:
        country = Country.objects.get(name__iexact=name)
        
        if request.method == 'GET':
            serializer = CountrySerializer(country)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        elif request.method == 'DELETE':
            country_name = country.name
            country.delete()
            return Response({
                'message': f'Country "{country_name}" deleted successfully'
            }, status=status.HTTP_200_OK)
    
    except Country.DoesNotExist:
        return Response({
            'error': 'Country not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
def get_status(request):
    """GET /status"""
    total_countries = Country.objects.count()
    latest_country = Country.objects.order_by('-last_refreshed_at').first()
    last_refreshed = latest_country.last_refreshed_at if latest_country else None
    
    return Response({
        'total_countries': total_countries,
        'last_refreshed_at': last_refreshed
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_summary_image(request):
    """GET /countries/image"""
    image_path = ImageGenerator.get_image_path()
    
    if not os.path.exists(image_path):
        return Response({
            'error': 'Summary image not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    return FileResponse(open(image_path, 'rb'), content_type='image/png')