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
    # category = CategorySerializer(read_only=True)
    # suppliers = SupplierSerializer( read_only=True)

    # # Écriture (relations via ID)
    # category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(),  write_only=True)
    # suppliers =  serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all(),write_only=True)

    class Meta:
        model = Product
        fields = "__all__"

    def validate(self, data):
        if data.get("price") and data["price"] <= 0:
            raise serializers.ValidationError(
                {"price": "Le prix doit être supérieur à zéro."}
            )
        return data
    
class ProductListSerializer(serializers.ModelSerializer):
    

    # Écriture (relations via ID)

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

   
    suppliers_name = serializers.CharField(
        # many=True,
        read_only=True,
        source="suppliers.name",
    )


    class Meta:
        model = Product
        fields = ["id", "name", "description", "price",  "category", "category_name",
            "suppliers", "suppliers_name" ,"created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

 