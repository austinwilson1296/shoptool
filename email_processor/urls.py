from django.urls import path
from .views import process_data

urlpatterns = [
    path("process_data/", process_data, name="process_data"),
]
