from django.db import models
from enum import Enum

class Status(Enum):
    PENDING = "pending"
    SHIPPED = "shipped"
    DELIVERED = "delivered"

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

class Order(models.Model):
    purchase_order_number = models.CharField(max_length=120, unique=True)
    ashley_order_number = models.CharField(max_length=120, unique=True)
    ashley_model_number = models.CharField(max_length=120)
    model_description = models.CharField(max_length=120)
    shipping_method = models.CharField(max_length=120)
    tracking_number = models.CharField(max_length=120, blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=Status.choices(), default=Status.PENDING.value
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.purchase_order_number} - {self.ashley_model_number}"

class Part(models.Model):
    part_number = models.CharField(max_length=120)
    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField()
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="parts")

    def __str__(self):
        return f"Part {self.part_number} - {self.description} ({self.quantity})"

