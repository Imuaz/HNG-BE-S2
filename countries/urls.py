from django.urls import path
from . import views

urlpatterns = [
    path('refresh', views.refresh_countries, name='refresh-countries'),
    path('image', views.get_summary_image, name='get-summary-image'),  # Before <str:name>
    path('', views.list_countries, name='list-countries'),
    path('<str:name>', views.country_detail, name='country-detail'),  # Handles GET and DELETE
]