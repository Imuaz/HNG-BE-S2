from django.urls import path
from . import views

urlpatterns = [
    path('refresh', views.refresh_countries, name='refresh-countries'),
    path('', views.list_countries, name='list-countries'),
    path('image', views.get_summary_image, name='get-summary-image'),
    path('<str:name>', views.get_country, name='get-country'),
    path('<str:name>/delete', views.delete_country, name='delete-country'),
]