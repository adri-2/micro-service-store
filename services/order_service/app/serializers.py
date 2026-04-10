from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from .models import Order, OrderItem
from  .services import get_product, get_user,get_customer
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
         
            "total_amount",
            "items",
            "items_input",
            "created_at",
            "status",
            "updated_at",
        ]
        read_only_fields = ["id", "total_amount", "created_at", "updated_at"]
    
    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items_input", [])
        request = self.context.get("request")
        access_token = None
        if request is not None:
            access_token = request.META.get("HTTP_AUTHORIZATION")
        
        if not items_data:
            raise serializers.ValidationError(
                {"items_input": "Au moins un item obligatoire."}
            )
            
        order = Order.objects.create(**validated_data)
        
        for item in items_data:
            product_id = str(item["product_id"])
            quantity = item["quantity"]
            
            product = get_product(product_id, access_token=access_token)
            unit_price = Decimal(str(product["price"]))
            
            if not product:
                raise serializers.ValidationError(
                    {"items_input": f"Produit {product_id} introuvable."}
                )
            
            # if not check_and_decrement_stock(product_id, quantity):
            #     raise serializers.ValidationError(
            #         {"items_input": f"Stock insuffisant pour le produit {product_id}."}
            #     )
            
            OrderItem.objects.create(
                order=order,
                product_id=product_id,
                product_name=product["name"],
                unit_price=unit_price,
                quantity=quantity,
                subtotal=unit_price * quantity
            )
            # OrderItem.save()
            
        order.update_total()
        return order
    
class OrderListSerializer(OrderSerializer):
    user_name = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Évitez les appels HTTP répétés pour des identifiants identiques lors de la sérialisation de la liste.
        self._user_cache = {}
        self._customer_cache = {}

    class Meta(OrderSerializer.Meta):
       
        fields = [
            "id",
            "user_id",
            "client_id",
            "status",
            "total_amount",
            "user_name",
            "customer_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
        
    def get_user_name(self, obj):
        request = self.context.get("request")
        user_id = str(obj.user_id)
        access_token = None
        # Récupérez le token d'accès depuis les en-têtes de la requête pour les appels aux services externes.
        if request is not None:
            access_token = request.META.get("HTTP_AUTHORIZATION")

        # Utilisez un cache pour éviter les appels HTTP répétés pour les mêmes identifiants d'utilisateur.
        if user_id in self._user_cache:
            return self._user_cache[user_id]

        try:
            user = get_user(user_id, access_token=access_token)
            username = user.get("username", "Inconnu")
        except (NotFound, ValidationError):
            username = "Inconnu"

        self._user_cache[user_id] = username
        return username
        
        
    def get_customer_name(self,obj):
        request = self.context.get("request")
        customer_id = str(obj.client_id)
        access_token = None
        if request is not None:
            access_token = request.META.get("HTTP_AUTHORIZATION")

        if customer_id in self._customer_cache:
            return self._customer_cache[customer_id]

        try:
            customer = get_customer(customer_id,access_token=access_token)
            username = f"{customer.get('first_name','Inconnu')} {customer.get('last_name','')}"
        except (NotFound, ValidationError):
            username = "Inconnu"

        self._customer_cache[customer_id] = username
        return username