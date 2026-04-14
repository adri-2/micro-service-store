from datetime import timezone
from .tasks import process_order_creation
from django.http import JsonResponse
from django.shortcuts import render
from pydantic_core import ValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response
import time
from .models import Order, OrderItem
from .serializers import (OrderDetailSerializer, OrderListSerializer,
                          OrderSerializer)

from django.core.cache import cache
import hashlib
# Create your views here.

CACHE_TTL_SECONDS = 60 * 5 

def _build_cache_key(prefix, request):
    path_hash = hashlib.md5(request.get_full_path().encode("utf-8")).hexdigest()
    return f"api-cache:{prefix}:{path_hash}"

def _invalidate_api_cache():
    if hasattr(cache,"delete_pattern"):
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



def health(request):
    return JsonResponse({"status": "ok",
                         "message": "Order service is healthy."})
    
class OrderViewSet(viewsets.ModelViewSet):
    # import time

    queryset = Order.objects.prefetch_related("items")
    # serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def list(self, request, *args, **kwargs):
        cache_key = _build_cache_key("orders:list",request)
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return Response(cached_data)
        
        response =  super().list(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            cache.set(cache_key,response.data,CACHE_TTL_SECONDS)
        
        return response
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return OrderSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer
    
    def perform_create(self, serializer):
        t1 = time.time()
        
        # Étape A : Appel API externe
        # ... ton code ...
        print(f"DEBUG: Appel API externe: {time.time() - t1}s")
        
        t2 = time.time()
        # Étape B : Sauvegarde BDD
        order = serializer.save()
        _invalidate_api_cache()
        print(f"DEBUG: Sauvegarde BDD: {time.time() - t2}s")        
        access_token = self.request.META.get("HTTP_AUTHORIZATION")
        process_order_creation.delay(str(order.id), access_token)    
        t3 = time.time()
        # Étape C : Envoi email ou autre
        # ... ton code ...
        print(f"DEBUG: Tâche post-création: {time.time() - t3}s")
        
    def perform_update(self, serializer):
        serializer.save()
        _invalidate_api_cache()
        
        
    def perform_destroy(self, instance):
        instance.delete()
        _invalidate_api_cache()
    
    
    def get_queryset(self):
        qs = Order.objects.prefetch_related("items")
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs
         
        
    @action(
        detail=True,
        methods=['post'],
        url_path='confirm'
    )
    def confirm(self,request,pk=None):
        order = self.get_object()
        if order.status != Order.StatusChoices.PENDING:
            return Response(
                {"detail":"Seules les commandes Pending peuvent être confirmées."},
                status=status.HTTP_400_BAD_REQUEST
            ) 
        order.status = Order.StatusChoices.CONFIRMED
        order.save(update_fields=["status","updated_at"])
        serializer = self.get_serializer(order)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
