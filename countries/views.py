from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import FileResponse
from django.db.models import F
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Country
from .serializers import CountrySerializer, CountryFilterSerializer
from .services import CountryService, ExternalAPIError
from .utils import ImageGenerator
import os


@extend_schema(
    summary="API Home - Project Information",
    description="Returns API information, available endpoints, deployment status, and links to interactive documentation.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "project": {"type": "string"},
                "description": {"type": "string"},
                "version": {"type": "string"},
                "status": {"type": "string"},
                "deployment": {"type": "string"},
                "documentation": {"type": "object"},
                "endpoints": {"type": "object"},
            },
        }
    },
    tags=["General"],
)
@api_view(["GET"])
def home(request):
    """GET / - API home with project information and documentation links"""
    total_countries = Country.objects.count()
    latest_country = Country.objects.order_by("-last_refreshed_at").first()
    last_refreshed = latest_country.last_refreshed_at if latest_country else None

    # Get the base URL from the request
    base_url = request.build_absolute_uri("/")[:-1]

    return Response(
        {
            "project": "Country Currency & Exchange API",
            "description": "RESTful API for country data, currency exchange rates, and GDP calculations",
            "version": "1.0.0",
            "status": "live",
            "deployment": "PythonAnywhere",
            "statistics": {
                "total_countries": total_countries,
                "last_refreshed_at": last_refreshed,
            },
            "documentation": {
                "swagger_ui": f"{base_url}/docs",
                "redoc": f"{base_url}/redoc",
                "openapi_schema": f"{base_url}/schema",
            },
            "endpoints": {
                "refresh_countries": f"{base_url}/countries/refresh",
                "list_countries": f"{base_url}/countries",
                "get_country": f"{base_url}/countries/{{name}}",
                "delete_country": f"{base_url}/countries/{{name}}",
                "status": f"{base_url}/status",
                "summary_image": f"{base_url}/countries/image",
            },
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="Refresh Countries Data",
    description="Fetches country data from external APIs (REST Countries and Exchange Rate API), updates the database, and generates a summary image.",
    request=None,
    responses={
        200: {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "total_countries": {"type": "integer"},
                "created": {"type": "integer"},
                "updated": {"type": "integer"},
                "last_refreshed_at": {"type": "string", "format": "date-time"},
            },
        },
        503: {"description": "External data source unavailable"},
        500: {"description": "Internal server error"},
    },
    examples=[
        OpenApiExample(
            "Success Response",
            value={
                "message": "Countries refreshed successfully",
                "total_countries": 250,
                "created": 10,
                "updated": 240,
                "last_refreshed_at": "2026-01-28T16:00:00Z",
            },
            response_only=True,
        )
    ],
    tags=["Countries"],
)
@api_view(["POST"])
def refresh_countries(request):
    """POST /countries/refresh"""
    try:
        result = CountryService.refresh_countries()

        try:
            ImageGenerator.generate_summary_image()
        except Exception as e:
            print(f"Image generation failed: {e}")

        return Response(
            {
                "message": "Countries refreshed successfully",
                "total_countries": result["total_countries"],
                "created": result["created"],
                "updated": result["updated"],
                "last_refreshed_at": result["last_refreshed_at"],
            },
            status=status.HTTP_200_OK,
        )

    except ExternalAPIError as e:
        return Response(
            {"error": "External data source unavailable", "details": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    except Exception as e:
        return Response(
            {"error": "Internal server error", "details": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    summary="List All Countries",
    description="Returns a list of all countries with optional filtering by region or currency, and sorting capabilities.",
    parameters=[
        OpenApiParameter(
            name="region",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by region (e.g., Africa, Europe, Asia)",
            required=False,
        ),
        OpenApiParameter(
            name="currency",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by currency code (e.g., NGN, USD, EUR)",
            required=False,
        ),
        OpenApiParameter(
            name="sort",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Sort results",
            required=False,
            enum=[
                "gdp_desc",
                "gdp_asc",
                "population_desc",
                "population_asc",
                "name_desc",
                "name_asc",
            ],
        ),
    ],
    responses={
        200: CountrySerializer(many=True),
        400: {"description": "Invalid query parameters"},
    },
    examples=[
        OpenApiExample(
            "Filter by Region", value="?region=Africa", parameter_only=("region",)
        ),
        OpenApiExample("Sort by GDP", value="?sort=gdp_desc", parameter_only=("sort",)),
    ],
    tags=["Countries"],
)
@api_view(["GET"])
def list_countries(request):
    """GET /countries with filters and sorting"""
    filter_serializer = CountryFilterSerializer(data=request.query_params)
    if not filter_serializer.is_valid():
        return Response(
            {"error": "Invalid query parameters", "details": filter_serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    queryset = Country.objects.all()
    validated_data = filter_serializer.validated_data

    if "region" in validated_data:
        queryset = queryset.filter(region__iexact=validated_data["region"])

    if "currency" in validated_data:
        queryset = queryset.filter(currency_code__iexact=validated_data["currency"])

    # FIX: Handle NULL values in GDP sorting
    if "sort" in validated_data:
        sort_param = validated_data["sort"]

        if sort_param == "gdp_desc":
            queryset = queryset.order_by(F("estimated_gdp").desc(nulls_last=True))
        elif sort_param == "gdp_asc":
            queryset = queryset.order_by(F("estimated_gdp").asc(nulls_last=True))
        elif sort_param == "population_desc":
            queryset = queryset.order_by("-population")
        elif sort_param == "population_asc":
            queryset = queryset.order_by("population")
        elif sort_param == "name_desc":
            queryset = queryset.order_by("-name")
        elif sort_param == "name_asc":
            queryset = queryset.order_by("name")

    serializer = CountrySerializer(queryset, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get or Delete Country",
    description="Retrieve details of a specific country by name or delete it from the database.",
    parameters=[
        OpenApiParameter(
            name="name",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.PATH,
            description="Country name (case-insensitive)",
            required=True,
        )
    ],
    responses={200: CountrySerializer, 404: {"description": "Country not found"}},
    examples=[
        OpenApiExample(
            "Country Details",
            value={
                "id": 1,
                "name": "Nigeria",
                "capital": "Abuja",
                "region": "Africa",
                "population": 206139589,
                "currency_code": "NGN",
                "exchange_rate": "1600.230000",
                "estimated_gdp": "25767448125.20",
                "flag_url": "https://flagcdn.com/ng.svg",
                "last_refreshed_at": "2026-01-28T16:00:00Z",
            },
            response_only=True,
        )
    ],
    tags=["Countries"],
)
@api_view(["GET", "DELETE"])
def country_detail(request, name):
    """GET or DELETE /countries/:name"""
    try:
        country = Country.objects.get(name__iexact=name)

        if request.method == "GET":
            serializer = CountrySerializer(country)
            return Response(serializer.data, status=status.HTTP_200_OK)

        elif request.method == "DELETE":
            country_name = country.name
            country.delete()
            return Response(
                {"message": f'Country "{country_name}" deleted successfully'},
                status=status.HTTP_200_OK,
            )

    except Country.DoesNotExist:
        return Response(
            {"error": "Country not found"}, status=status.HTTP_404_NOT_FOUND
        )


@extend_schema(
    summary="Get API Status",
    description="Returns the total number of countries in the database and the last refresh timestamp.",
    responses={
        200: {
            "type": "object",
            "properties": {
                "total_countries": {"type": "integer"},
                "last_refreshed_at": {
                    "type": "string",
                    "format": "date-time",
                    "nullable": True,
                },
            },
        }
    },
    examples=[
        OpenApiExample(
            "Status Response",
            value={"total_countries": 250, "last_refreshed_at": "2026-01-28T16:00:00Z"},
            response_only=True,
        )
    ],
    tags=["General"],
)
@api_view(["GET"])
def get_status(request):
    """GET /status"""
    total_countries = Country.objects.count()
    latest_country = Country.objects.order_by("-last_refreshed_at").first()
    last_refreshed = latest_country.last_refreshed_at if latest_country else None

    return Response(
        {"total_countries": total_countries, "last_refreshed_at": last_refreshed},
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="Get Summary Statistics Image",
    description="Returns a PNG image with country statistics and visualizations. The image is generated during the refresh operation.",
    responses={
        200: {"type": "string", "format": "binary", "description": "PNG image file"},
        404: {"description": "Summary image not found. Run /countries/refresh first."},
    },
    tags=["Countries"],
)
@api_view(["GET"])
def get_summary_image(request):
    """GET /countries/image"""
    image_path = ImageGenerator.get_image_path()

    if not os.path.exists(image_path):
        return Response(
            {"error": "Summary image not found"}, status=status.HTTP_404_NOT_FOUND
        )

    return FileResponse(open(image_path, "rb"), content_type="image/png")
