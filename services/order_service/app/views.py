from django.http import JsonResponse
from django.shortcuts import render
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Order, OrderItem
from .serializers import (OrderDetailSerializer, OrderListSerializer,
                          OrderSerializer)
# Create your views here.
from .services import (get_customer, get_customers_bulk, get_product, get_user,
                       get_users_bulk)


def health(request):
    return JsonResponse({"status": "ok",
                         "message": "Order service is healthy."})
    
class OrderViewSet(viewsets.ModelViewSet):

    queryset = Order.objects.prefetch_related("items")
    # serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return OrderSerializer
        elif self.action == 'list':
            return OrderListSerializer
        return OrderDetailSerializer
    
    def list(self, request, *args, **kwargs):
        self.queryset = self.get_queryset()
        
        user_ids = list(set(str(o.user_id) for o in self.queryset))
        customer_ids = list(set(str(o.client_id) for o in self.queryset))
        
        access_token = request.META.get("HTTP_AUTHORIZATION")
        
        try:
            users_map = get_users_bulk(user_ids,access_token)
        except Exception:
            users_map = {}
            
        try:
            customers_map = get_customers_bulk(customer_ids,access_token)
        except Exception:
            customers_map = {}
            
        serializer = self.get_serializer(
            self.queryset,
            many=True,
            context={
                "users_map":users_map,
                "customers_map":customers_map
            }
        )
        return Response(serializer.data)
    
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
        
