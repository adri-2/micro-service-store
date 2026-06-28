import hashlib

from django.core.cache import cache
# Create your views here.
# def index(request):
#     return render(request, "index.html")
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from rest_framework.exceptions import ValidationError
from .models import Category, Product, Supplier
from .serializers import (BulkIdsSerializer, CategorySerializer,
                          ProductListSerializer, ProductSerializer,
                          SupplierSerializer,StockActionSerializer)

CACHE_TTL_SECONDS = 60 * 5


def _build_cache_key(prefix, request):
    path_hash = hashlib.md5(request.get_full_path().encode("utf-8")).hexdigest()
    return f"api-cache:{prefix}:{path_hash}"


def _invalidate_api_cache():
    # delete_pattern est disponible avec django-redis; fallback clear pour les autres backends.
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern("api-cache:*")
    else:
        cache.clear()


@permission_classes([permissions.AllowAny])
def cache_probe(request):
    cache_key = "api-cache:debug:order"
    ttl_seconds = 30

    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return JsonResponse(
            {
                "cache": "HIT",
                "key": cache_key,
                "ttl_seconds": ttl_seconds,
                "payload": cached_payload,
            }
        )

    payload = {
        "generated_at": timezone.now().isoformat(),
        "message": "Payload genere sur MISS puis stocke dans Redis.",
    }
    cache.set(cache_key, payload, ttl_seconds)
    return JsonResponse(
        {
            "cache": "MISS",
            "key": cache_key,
            "ttl_seconds": ttl_seconds,
            "payload": payload,
        }
    )

@permission_classes([permissions.AllowAny])
def health(request):
    return JsonResponse({"status": "ok",
                         "message": "Product service is healthy."})


class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def list(self, request, *args, **kwargs):
        cache_key = _build_cache_key("categories:list", request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(cache_key, response.data, CACHE_TTL_SECONDS)
        return response

    def perform_create(self, serializer):
        serializer.save()
        _invalidate_api_cache()

    def perform_update(self, serializer):
        serializer.save()
        _invalidate_api_cache()

    def perform_destroy(self, instance):
        instance.delete()
        _invalidate_api_cache()
    


class SupplierViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

    def list(self, request, *args, **kwargs):
        cache_key = _build_cache_key("suppliers:list", request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(cache_key, response.data, CACHE_TTL_SECONDS)
        return response

    def perform_create(self, serializer):
        serializer.save()
        _invalidate_api_cache()

    def perform_update(self, serializer):
        serializer.save()
        _invalidate_api_cache()

    def perform_destroy(self, instance):
        instance.delete()
        _invalidate_api_cache()


class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Product.objects.select_related("category").select_related("suppliers")
    # serializer_class = ProductSerializer
    
    def retrieve(self, request, *args, **kwargs):
        cache_key = _build_cache_key("product:detail", request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        response = super().retrieve(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(cache_key, response.data, CACHE_TTL_SECONDS)
        
        return response

    def list(self, request, *args, **kwargs):
        cache_key = _build_cache_key("products:list", request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)

        response = super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(cache_key, response.data, CACHE_TTL_SECONDS)
        return response

    def get_serializer_class(self):
        if self.action in ['create','update','partial_update']:
            return ProductSerializer
        elif self.action == 'list':
            return ProductListSerializer
        else:
            return ProductSerializer

    def perform_create(self, serializer):
        serializer.save()
        _invalidate_api_cache()

    def perform_update(self, serializer):
        serializer.save()
        _invalidate_api_cache()

    def perform_destroy(self, instance):
        instance.delete()
        _invalidate_api_cache()


class ProductBulkViewService(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = BulkIdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]

        cache_key = f"api-cache:products:bulk:{','.join(sorted(str(i) for i in ids))}"
        cached_results = cache.get(cache_key)
        if cached_results is not None:
            return Response({"results": cached_results}, status=status.HTTP_200_OK)

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

        cache.set(cache_key, results, CACHE_TTL_SECONDS)

        return Response({"results": results}, status=status.HTTP_200_OK)

class ReserveStockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self,request):
        serializer = StockActionSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data["items"]
        product_ids = [item["product_id"] for item in items]

        products = Product.objects.select_for_update().filter(
            id__in=product_ids
        ).only("id",
               "stock",
               "reserved_stock"   )
        product_map = {
            str(product.id):product
            for product in products
        }
        updated_products = []


        for item in items:
            product = product_map.get(str(item["product_id"]))
            if product is None:
                raise ValidationError(  f"Produit {item['product_id']} introuvable.")
            qty = item["quantity"]
            if product.available_stock < qty:
                raise ValidationError(
                    f"stock insuffisant pour {product.id}"
                )
            product.reserved_stock += qty
            updated_products.append(product)
        Product.objects.bulk_update(updated_products,["reserved_stock"])
            
        return Response(
            {"detail":"Stock réservé"},
            status=status.HTTP_200_OK
        )

class ConfirmStockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self,request):
        serializer = StockActionSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data["items"]
        product_ids = [item["product_id"] for item in items]

        products = Product.objects.select_for_update().filter(
            id__in=product_ids
        ).only("id",
               "stock",
               "reserved_stock"   )
        product_map = {
            str(product.id):product
            for product in products
        }
        updated_products = []

        for item in items:
            product = product_map.get(str(item["product_id"]))
            if product is None:
                raise ValidationError(  f"Produit {item['product_id']} introuvable.")
            qty = item["quantity"]
            if product.available_stock < qty:
                raise ValidationError(
                    f"stock insuffisant pour {product.name}"
                )
            product.stock -= qty
            product.reserved_stock -= qty
            updated_products.append(product)
        Product.objects.bulk_update(
            updated_products,
            ["stock",
              "reserved_stock",]
        )


        return Response(
            {"detail": "Stock confirmé."},
            status=status.HTTP_200_OK
        )
    
class ReleaseStockView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = StockActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items = serializer.validated_data["items"]
        product_ids = [item["product_id"] for item in items]

        products = Product.objects.select_for_update().filter(
            id__in=product_ids
        ).only(
            "id",
            "reserved_stock"
        )

        product_map = {
            str(product.id):product
            for product in products 
        }
        updated_products = []

        for item in items:
            product = product_map.get(str(item["product_id"]))
            if product is None:
                raise ValidationError(
                    f"Produit{item['product_id']} introuvable."
                )
            qty = item["quantity"]
            if product.reserved_stock < qty:
                raise ValidationError(
                    f"Le stock réservé est insuffisant pour {product.id}"
                )
            product.reserved_stock -= qty
            updated_products.append(product)
        Product.objects.bulk_update(
            updated_products,
            ["reserved_stock"]
        )

        return Response(
            {"detail": "Stock libéré."},
            status=status.HTTP_200_OK
        )
    