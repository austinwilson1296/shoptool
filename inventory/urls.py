from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import *

urlpatterns = [
    path('download-csv/', download_csv_report, name='download_csv_report'),
    path('Product/new/', ProductCreateView.as_view(), name='product_create'),
    path('Product/<int:pk>/', ProductDetailView.as_view(), name='product_lookup'),
    path('Checkout/', checkout_inventory_view, name='checkout_create'),
    path('inventory/<str:abbreviation>/', supply_levels, name='inventory_comparison'),
    path('', login_required(HomePageView.as_view()), name='home'),
    path('chart/', checkout_chart_view,name='checkout_chart'),
    path('get_inventory_items/', get_inventory_items, name='get_inventory_items'),
    path('ajax/load-checked-out-by/', load_checked_out_by, name='ajax_load_checked_out_by'),
    path('transfer-inventory/', transfer_inventory_view, name='transfer_inventory'),
    path('inventory_lookup/',inventory_lookup_view,name='inventory_lookup_view'),
    path('supply_request/',supply_request,name='supply_request'),
    path('submit-request/', submit_request, name='submit_request'),
    path('approve/', approve_request, name='approve_request'),
    path('deny/', deny_request, name='deny_request'),
    path('part_order/', PartsOrderView.as_view(), name='parts_order_view'),
    path('part_order/<int:pk>/', OrderDetailView.as_view(), name='order_lookup')

]