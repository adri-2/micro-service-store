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


from app.views import (ClientBulkViewService, ClientDetailService,
                       ClientViewSet, LoginView, LogoutView, MeView,
                       RefreshView, RegisterView, UserBulkViewService,
                       UserDetailViewService, VerifyTokenView, health)
from django.urls import path
from rest_framework.routers import DefaultRouter

route = DefaultRouter()
route.register(r'customers', ClientViewSet, basename='customer')

urlpatterns = [
    path("health/", health),
    path("auth/register/", RegisterView.as_view()),
    path("auth/login/", LoginView.as_view()),
    path("auth/refresh/", RefreshView.as_view()),
    path("auth/blacklist/", LogoutView.as_view()),
    path("auth/me/", MeView.as_view()),
    path("auth/verify/", VerifyTokenView.as_view()),
    path("user/me/<str:pk>/", UserDetailViewService.as_view()),
    path("customer/me/<str:pk>/", ClientDetailService.as_view()),
    path("user/bulk/", UserBulkViewService.as_view()),
    path("customer/bulk/", ClientBulkViewService.as_view()),
  
]+ route.urls


