"""
URL configuration for india_blockchain_voting project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from users.admin import django_admin_site as custom_admin

# API Documentation - commented out until drf_yasg is installed
# schema_view = get_schema_view(
#     openapi.Info(
#         title="India Blockchain Voting API",
#         default_version='v1',
#         description="A comprehensive blockchain-based voting system for Indian elections",
#         terms_of_service="https://www.google.com/policies/terms/",
#         contact=openapi.Contact(email="admin@blockchainvoting.gov.in"),
#         license=openapi.License(name="MIT License"),
#     ),
#     public=True,
#     permission_classes=(permissions.AllowAny,),
# )

urlpatterns = [
    # Admin
    path('admin/', custom_admin.urls),
    path('admin/elections/', include(('elections.admin_urls', 'admin_elections'), namespace='admin_elections')),
    
    # Users API
    path('api/users/', include('users.urls')),
    
    # Elections API (different namespace)
    path('api/elections/', include(('elections.urls', 'api_elections'), namespace='api_elections')),
    
    # Blockchain API
    path('api/blockchain/', include('blockchain.urls')),
    
    # Reports API
    path('api/reports/', include('reports.urls')),
      # Frontend Elections pages
    path('', include('elections.urls')),
    path('elections/', include('elections.urls', namespace='elections_prefix')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
