import hashlib
import time
from datetime import timezone
from .services import confirm_stock, release_stock
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from pydantic_core import ValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response

from .models import Order, OrderItem
from .serializers import (OrderDetailSerializer, OrderListSerializer,
                          OrderSerializer)
from .tasks import process_order_creation

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
        print(f"DEBUG: Appel API externe: {time.time() - t1}s")

        t2 = time.time()
        access_token = self.request.META.get("HTTP_AUTHORIZATION")
        items_data = serializer.initial_data.get("items_input", [])
        order = serializer.save(
            access_token=access_token
        )
        _invalidate_api_cache()
        print(f"DEBUG: Sauvegarde BDD: {time.time() - t2}s")

        
        process_order_creation.delay(str(order.id), access_token)

        t3 = time.time()
        print(f"DEBUG: Tâche post-création: {time.time() - t3}s")
        
    def perform_update(self, serializer):
        serializer.save()
        _invalidate_api_cache()
        
        
    def perform_destroy(self, instance):
 
        instance.delete()
        _invalidate_api_cache()
    
    def destroy(self,rquest, *args,**kwargs):
        instance  = self.get_object()

        if instance.status == Order.StatusChoices.CONFIRMED:
            return Response(
            {"detail": "Une commande confirmée ne peut pas être supprimée."},
            status=status.HTTP_400_BAD_REQUEST
        )
        self.perform_destroy(instance)
        _invalidate_api_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
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
        items = [
            { "product_id": str(item.product_id),
            "quantity": item.quantity,} 
            for item in order.items.all()
        ]
        access_token = request.META.get('HTTP_AUTHORIZATION')
        confirm_stock(items,access_token)
        order.status = Order.StatusChoices.CONFIRMED
        order.save(update_fields=["status","updated_at"])
        _invalidate_api_cache()
        serializer = self.get_serializer(order)
        
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @action(detail=True,methods=["post"],url_path="cancel")    
    def cancel(self,request,pk=None):
        order = self.get_object()

        if order.status not in (
            Order.StatusChoices.DRAFT,
            Order.StatusChoices.PENDING,
        ):
            return Response(
                 {"detail": "Cette commande ne peut plus être annulée."},
            status=status.HTTP_400_BAD_REQUEST,
            )
        items = [
              { "product_id": str(item.product_id),
            "quantity": item.quantity,} 
            for item in order.items.all()
        ]
        access_token = request.META.get('HTTP_AUTHORIZATION')

        release_stock(items,access_token)
        order.status = Order.StatusChoices.CANCELLED
        order.save(update_fields=["status","updated_at"])
        _invalidate_api_cache()

        serializer =self.get_serializer(order)

        return Response(serializer.data)

    # @action(detail=True,methods=["post"],url_path="archive")
    # def archive(self,request,pk=None):
    #     order = self.get_object()
    #     if order.status not in (
    #         Order.StatusChoices.DRAFT,
    #         Order.StatusChoices.PENDING
    #     ):
    #         return Response(
    #             {"detail":"Cette commande ne peut plus être archivee."}
    #         )
    #     order.status = Order.StatusChoices.ARCHIVED
    #     order.save(update_fields=["status","update_at"])

    #     serializer = self.get_serializer(order)
    #     return Response(serializer.data)