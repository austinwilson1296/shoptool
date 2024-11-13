from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
import pytz


class Product(models.Model):
    name = models.CharField(max_length=50, null=False, blank=False)
    vendor = models.ForeignKey('Vendor', on_delete=models.CASCADE, null=False, blank=False, default=0)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=False, blank=False, default=0)
    min_order_qty = models.IntegerField(null=False, blank=False, default=0)
    description = models.TextField(null=False, blank=False)
    order_method = models.CharField(max_length=50, null=False, blank=False)
    safety_stock = models.IntegerField(null=False, blank=False, default=0)

    def __str__(self):
        return self.name[:50]

    def get_absolute_url(self):
        return reverse("product_lookup", kwargs={"pk": self.pk})


class Center(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    address = models.CharField(max_length=255, null=False, blank=False)
    storis_Abbreviation = models.CharField(max_length=3, null=False, blank=False)

    def __str__(self):
        return self.storis_Abbreviation
    
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    distribution_center = models.ForeignKey(Center,on_delete=models.SET_NULL, null=True)


class Vendor(models.Model):
    vendor_code = models.CharField(max_length=3, null=False, blank=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    phone_number = models.CharField(max_length=11, null=False, blank=False)
    email = models.EmailField(max_length=255, null=False, blank=False)

    def __str__(self):
        return self.vendor_code


class Inventory(models.Model):
    distribution_center = models.ForeignKey('Center', on_delete=models.CASCADE, null=False, blank=False)
    product = models.ForeignKey('Product', on_delete=models.CASCADE, null=False, blank=False)
    quantity = models.IntegerField(null=False, blank=False)
    stock_location = models.CharField(max_length=50, null=False, blank=False)
    stock_loc_level = models.CharField(max_length=50)

    def __str__(self):
        return (f'Product Name : {self.product.name} | '
                f'Quantity : {self.quantity} |'
                f'DC : {self.distribution_center.name} |'
                f'Stock Location : {self.stock_location} |'
                f'Stock Level : {self.stock_loc_level} |')


class CheckedOutBy(models.Model):
    name = models.CharField(max_length=100)
    distribution_center = models.ForeignKey('Center', on_delete=models.CASCADE, null=False, blank=False)

    def __str__(self):
        return self.name


class Checkout(models.Model):
    inventory_item = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    checked_out_by = models.ForeignKey(CheckedOutBy, on_delete=models.CASCADE)
    checkout_date = models.DateTimeField(default=timezone.now)
    quantity = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True)

    def __str__(self):
        return (f'{self.checked_out_by}'
                f'{self.checkout_date}'
                f'{self.inventory_item}'
                f'{self.user}')
    @property
    def total_cost(self):
        return self.quantity * self.inventory_item.product.cost
    

class TransactionHistory(models.Model):
    ACTION_CHOICES = [
        ('receive', 'Received'),
        ('transfer', 'Transferred'),
        ('checkout', 'Checked Out'),
    ]
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    inventory_item = models.ForeignKey('Inventory', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    user_center = models.CharField(max_length=100, null=True, blank=True)  # Store the center name or ID if needed
    timestamp = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.action} - {self.inventory_item} - {self.quantity} - {self.user.username if self.user else 'N/A'} - {self.timestamp}"
    
    @property
    def formatted_timestamp(self):
        # Convert timestamp to EST and format it
        est = pytz.timezone('US/Eastern')  # Eastern Standard Time
        timestamp_est = self.timestamp.astimezone(est)  # Convert to EST
        return timestamp_est.strftime('%Y-%m-%d %H:%M:%S')  # Format the timestamp

