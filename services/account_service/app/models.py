import uuid

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db import models


class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class User(AbstractBaseUser, BaseModel):
   
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)    

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    def __str__(self):
        return self.email


class Client(BaseModel):
   
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    def clean(self):
        if Client.objects.filter(email__iexact=self.email).exclude(pk=self.pk).exists():
            raise ValidationError("Cet email existe déjà.")

    def __str__(self):
        return f"{self.first_name} {self.last_name}"