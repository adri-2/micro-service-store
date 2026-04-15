from django.shortcuts import render
import hashlib
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
from django.core.cache import cache
from django.utils import timezone
# Create your views here.
# def index(request):
#     return render(request, "index.html")
from django.http import JsonResponse

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