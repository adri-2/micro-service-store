from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Order, OrderItem
from .serializers import OrderSerializer
# Create your views here.
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "ok",
                         "message": "Order service is healthy."})
    
class OrderViewSet(viewsets.ModelViewSet):

    queryset = Order.objects.prefetch_related("items")
    serializer_class = OrderSerializer
