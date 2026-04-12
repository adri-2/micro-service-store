from django.http import JsonResponse
from django.shortcuts import render
from pydantic_core import ValidationError
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import time
from .models import Order, OrderItem
from .serializers import (OrderDetailSerializer, OrderListSerializer,
                          OrderSerializer)
# Create your views here.



def health(request):
    return JsonResponse({"status": "ok",
                         "message": "Order service is healthy."})
    
class OrderViewSet(viewsets.ModelViewSet):
    # import time

    queryset = Order.objects.prefetch_related("items")
    # serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
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
        serializer.save()
        print(f"DEBUG: Sauvegarde BDD: {time.time() - t2}s")
    
        t3 = time.time()
        # Étape C : Envoi email ou autre
        # ... ton code ...
        print(f"DEBUG: Tâche post-création: {time.time() - t3}s")
    
   

    def create(self, request, *args, **kwargs):
     
        start_time = time.time()
        
        # Ton code actuel
        response = super().create(request, *args, **kwargs)
        
        print(f"--- Temps d'exécution : {time.time() - start_time} secondes ---")
        return response
    
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
        
