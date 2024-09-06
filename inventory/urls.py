from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import HomePageView, ProductDetailView, ProductCreateView, CheckoutCreateView, supply_levels, download_csv_report, checkout_chart_view,get_inventory_items

urlpatterns = [
    path('download-csv/', download_csv_report, name='download_csv_report'),
    path('Product/new/', ProductCreateView.as_view(), name='product_create'),
    path('Product/<int:pk>/', ProductDetailView.as_view(), name='product_lookup'),
    path('Checkout/', CheckoutCreateView.as_view(), name='checkout_create'),
    path('inventory/<str:abbreviation>/', supply_levels, name='inventory_comparison'),
    path('', login_required(HomePageView.as_view()), name='home'),
    path('chart/', checkout_chart_view,name='checkout_chart'),
    path('get_inventory_items/', get_inventory_items, name='get_inventory_items')
]