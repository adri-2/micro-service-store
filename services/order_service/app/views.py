from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Order, OrderItem
from .serializers import OrderSerializer
# Create your views here.
from django.http import JsonResponse
from rest_framework import permissions

def health(request):
    return JsonResponse({"status": "ok",
                         "message": "Order service is healthy."})
    
class OrderViewSet(viewsets.ModelViewSet):

    queryset = Order.objects.prefetch_related("items")
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]  
    
    
    
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
        
