from decimal import Decimal

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError

from .services import reserve_stock

from .models import Order, OrderItem



class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "unit_price",
            "quantity",
            "subtotal",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

class OrderItemInputSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)
    class Meta:
        model = OrderItem
        fields = ["product_id", "quantity"]



class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    items_input = OrderItemInputSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user_id",
            "client_id",
            "user_name",
            "client_name",
            "total_amount",
            "items",
            "items_input",
            "created_at",
            "status",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "total_amount",
            "created_at",
            "updated_at",
            "user_name",
            "client_name",
        ]

    @transaction.atomic
    def create(self, validated_data):
        
        items_data = validated_data.pop("items_input", [])
        items_data = [
           { "product_id":str(item["product_id"]),
            "quantity":item["quantity"]}
            for item in items_data
        ]
        access_token = validated_data.pop("access_token")
        reserve_stock(items_data,access_token)

        # if not items_data:
        #     raise ValidationError({"items_input": "Au moins un item obligatoire."})

        order = Order.objects.create(
            user_id=validated_data["user_id"],
            client_id=validated_data["client_id"],
            user_name="En cours",
            client_name="En cours",
            status=Order.StatusChoices.DRAFT,
        )
        for item in items_data:
            OrderItem.objects.create(
                order=order,
                product_id=item["product_id"],
                quantity=item["quantity"],
                product_name="En cours",
                unit_price=Decimal("0.00"),
                subtotal=Decimal("0.00"),
            )

        return order
    
    
class OrderListSerializer(serializers.ModelSerializer):
    # user_name = serializers.SerializerMethodField()
    # customer_name = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta(OrderSerializer.Meta):
        model = Order
       
        fields = [
            "id",
            "user_id",
            "client_id",
            "status",
            "total_amount",
            "user_name",
            "client_name",
            "created_at",
            "updated_at",
            "items",
        ]
        read_only_fields = fields
        
    # def get_items (self, obj):
    #     return OrderItemSerializer(obj.items.all(), many=True).data
 
    

class OrderDetailSerializer(serializers.ModelSerializer):
    
    items = OrderItemSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = "__all__" 


class OrderStatusChange(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ["status","update_at"]
        read_only_fields = ["update_at"]
       
        
    
    
        
        