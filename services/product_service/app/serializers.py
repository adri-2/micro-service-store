from rest_framework import serializers
from .models import Category, Supplier, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class ProductSerializer(serializers.ModelSerializer):
    # Affichage en lecture
    category = CategorySerializer(read_only=True)
    suppliers = SupplierSerializer(many=True, read_only=True)

    # Écriture (relations via ID)
    category_id = serializers.UUIDField(write_only=True)
    supplier_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True
    )

    class Meta:
        model = Product
        fields = "__all__"

    def validate(self, data):
        if data.get("price") and data["price"] <= 0:
            raise serializers.ValidationError(
                {"price": "Le prix doit être supérieur à zéro."}
            )
        return data

    def create(self, validated_data):
        category_id = validated_data.pop("category_id")
        supplier_ids = validated_data.pop("supplier_ids", [])

        product = Product.objects.create(
            category_id=category_id,
            **validated_data
        )

        if supplier_ids:
            product.suppliers.set(supplier_ids)

        return product

    def update(self, instance, validated_data):
        category_id = validated_data.pop("category_id", None)
        supplier_ids = validated_data.pop("supplier_ids", None)

        if category_id:
            instance.category_id = category_id

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if supplier_ids is not None:
            instance.suppliers.set(supplier_ids)

        return instance