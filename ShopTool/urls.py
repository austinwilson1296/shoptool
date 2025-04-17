from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('users/', include('django.contrib.auth.urls')),
    path('users/', include('users.urls')),
    path('', include('inventory.urls')),
    path('orders/', include('email_processor.urls')),
    path('admin/', admin.site.urls),

]
