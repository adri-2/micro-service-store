import uuid
from django.db import models
from django.core.exceptions import ValidationError


from django.contrib.auth.base_user import AbstractBaseUser

# User vide qui ne crée qu'une table minimale
class EmptyUser(AbstractBaseUser):
    USERNAME_FIELD = 'id'
    
    class Meta:
        app_label = 'app'
class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Order(BaseModel):

    class StatusChoices(models.TextChoices):
        DRAFT = 'Draft', 'Draft'
        PENDING = 'Pending', 'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        CANCELLED = 'Cancelled', 'Cancelled'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user_id = models.UUIDField()  # ID du user auth
    user_name = models.CharField(max_length=150)  # Nom du user pour affichage
    client_id = models.UUIDField()   # ID venant du Clients Service
    client_name = models.CharField(max_length=150)  # Nom du client pour affichage

    status = models.CharField(
        max_length=10,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT
    )

    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    def update_total(self):
        total = self.items.aggregate(
            total=models.Sum("subtotal")
        )["total"] or 0

        self.total_amount = total
        self.save(update_fields=["total_amount"])
        
    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id}" 


class OrderItem(BaseModel):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # Snapshot produit
    product_id = models.UUIDField()
    product_name = models.CharField(max_length=150)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError("Quantité invalide.")

    def save(self, *args, **kwargs):
        self.subtotal = self.unit_price * self.quantity
        super().save(*args, **kwargs)
        self.order.update_total()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total()

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"