"""
URL configuration for core project.

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

from app.views import (CategoryViewSet, ProductBulkViewService, ProductViewSet,
                       SupplierViewSet, cache_probe, health,
                       ReleaseStockView,ReserveStockView,ConfirmStockView)
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi



schema_view = get_schema_view(
   openapi.Info(
      title="Product Service API",
      default_version='v1',
      description="API documentation for the Product Service",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@snippets.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

router = DefaultRouter()
router.register(r"categories", CategoryViewSet)
router.register(r"suppliers", SupplierViewSet)
router.register(r"products", ProductViewSet)


urlpatterns = [
    path("health/", health),
    path("cache-probe/", cache_probe),
    path("products/bulk/", ProductBulkViewService.as_view()),
     path(
        "products/stock/reserve/",
        ReserveStockView.as_view(),
        name="reserve-stock",
    ),
    path(
        "products/stock/confirm/",
        ConfirmStockView.as_view(),
        name="confirm-stock",
    ),
    path(
        "products/stock/release/",
        ReleaseStockView.as_view(),
        name="release-stock",
    ),
      path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
           path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
           path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
]
urlpatterns += router.urls
