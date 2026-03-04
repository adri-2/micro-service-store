from django.shortcuts import render

# Create your views here.
# def index(request):
#     return render(request, "index.html")
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok"})
from rest_framework import viewsets
from .models import Category, Supplier, Product
from .serializers import (
    CategorySerializer,
    SupplierSerializer,
    ProductSerializer
)


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category").prefetch_related("suppliers")
    serializer_class = ProductSerializer