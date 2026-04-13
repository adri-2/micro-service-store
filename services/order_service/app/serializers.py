from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from .models import Order, OrderItem
from  .services import get_product, get_user, get_customer, get_users_bulk, get_customers_bulk,get_products_bulk
from django.db import transaction
from decimal import Decimal


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
        request = self.context.get("request")

        access_token = None
        if request:
            access_token = request.META.get("HTTP_AUTHORIZATION")

        if not items_data:
            raise ValidationError({"items_input": "Au moins un item obligatoire."})

        #  SNAPSHOT ICI (BON ENDROIT)
        try:
            user = get_user(str(validated_data["user_id"]), access_token)
        except Exception:
            raise ValidationError({"user_id": "User introuvable."})

        try:
            customer = get_customer(str(validated_data["client_id"]), access_token)
        except Exception:
            raise ValidationError({"client_id": "Client introuvable."})

        #  création avec snapshot
        order = Order.objects.create(
            user_id=validated_data["user_id"],
            user_name=user.get("username", "Inconnu"),
            client_id=validated_data["client_id"],
            client_name=f"{customer.get('first_name','')} {customer.get('last_name','')}".strip(),
            status=Order.StatusChoices.DRAFT,
        )
        product_ids = [str(item['product_id']) for item in items_data]
        
        try:
            product_map = get_products_bulk(product_ids,access_token)
        except Exception:
            raise ValidationError("Erreur recuperation produits")

        #  items
        for item in items_data:
            product = product_map.get(str(item["product_id"]))
            if not product:
                raise ValidationError(   {"items_input": f"Produit {item['product_id']} introuvable"}
)
            unit_price = Decimal(str(product["price"]))

            OrderItem.objects.create(
                order=order,
                product_id=item["product_id"],
                product_name=product["name"],
                unit_price=unit_price,
                quantity=item["quantity"],
                subtotal=unit_price * item["quantity"],
            )

        order.update_total()
        return order
    
    
class OrderListSerializer(OrderSerializer):
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
    
    
    class Meta:
        model = Order
        fields = "__all__" 
        
       
        
    
    
        
        