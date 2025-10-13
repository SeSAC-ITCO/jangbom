from django.urls import path
from .views import *

app_name = 'point'

urlpatterns = [
    path('home/', point_home, name='point_home'),
    path('history/', point_history, name='point_history'),
    path('ranking/', point_ranking, name='point_ranking'),
    path('barcode/', barcode_view, name='barcode'),
]