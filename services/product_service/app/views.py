from django.shortcuts import render
from rest_framework import viewsets
from .models import Category, Supplier, Product
from .serializers import (
    CategorySerializer,
    SupplierSerializer,
    ProductSerializer,
    ProductListSerializer,
    BulkIdsSerializer,
)
from rest_framework.decorators import permission_classes
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
# Create your views here.
# def index(request):
#     return render(request, "index.html")
from django.http import JsonResponse

@permission_classes([permissions.AllowAny])
def health(request):
    return JsonResponse({"status": "ok",
                         "message": "Product service is healthy."})


class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    
    
            
    


class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.select_related("category").prefetch_related("suppliers")
    # serializer_class = ProductSerializer
    def get_serializer_class(self):
        if self.action in ['create','update','partial_update']:
            return ProductSerializer
        elif self.action == 'list':
            return ProductListSerializer
        else:
            return ProductSerializer


class ProductBulkViewService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        products = Product.objects.filter(id__in=ids).values(
            "id",
            "name",
            "price",
            "description",
            "stock",
            "category_id",
            "suppliers_id",
        )

        results = {
            str(item["id"]): {
                "id": str(item["id"]),
                "name": item["name"],
                "price": item["price"],
                "description": item["description"],
                "stock": item["stock"],
                "category": str(item["category_id"]),
                "suppliers": str(item["suppliers_id"]),
            }
            for item in products
        }

        return Response({"results": results}, status=status.HTTP_200_OK)