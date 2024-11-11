from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from .models import *
from .forms import *

class InventoryTransferViewTests(TestCase):

    def setUp(self):
        # Create a Center for the user
        self.center = Center.objects.create(
            name="Test Center",
            address="123 Test St",
            storis_Abbreviation="TST"
        )

        # Create a user and link the user to a UserProfile
        self.user = User.objects.create_user(
            username="testuser", password="password123"
        )
        self.user_profile = UserProfile.objects.create(
            user=self.user, distribution_center=self.center
        )

        # Create a product to transfer
        self.product = Product.objects.create(
            name="Test Product",
            cost=10.00
        )

        # Create an initial Inventory entry for the product
        self.initial_quantity = 100
        self.inventory = Inventory.objects.create(
            distribution_center=self.center,
            product=self.product,
            quantity=self.initial_quantity,
            stock_location="A1",
            stock_loc_level="1"
        )

    def test_transfer_inventory_successfully(self):
        # Log in the user
        self.client.login(username="testuser", password="password123")
        
        # Prepare the POST data for a valid transfer
        transfer_quantity = 10
        post_data = {
            'inventory_item': self.product.id,
            'quantity': transfer_quantity,
            'stock_location': "A1",
            'stock_loc_level': "1"
        }
        
        # Submit the POST request
        response = self.client.post(reverse('transfer_inventory'), post_data)
        
        # Check if the transfer was successful
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, self.initial_quantity - transfer_quantity)
        
        # Check if a success message is shown
        self.assertContains(response, "Inventory transferred successfully.")
        
    def test_transfer_inventory_insufficient_quantity(self):
        # Log in the user
        self.client.login(username="testuser", password="password123")
        
        # Try transferring more than the available quantity
        transfer_quantity = self.initial_quantity + 1  # Exceeds the available quantity
        post_data = {
            'inventory_item': self.product.id,
            'quantity': transfer_quantity,
            'stock_location': "A1",
            'stock_loc_level': "1"
        }
        
        # Submit the POST request
        response = self.client.post(reverse('transfer_inventory'), post_data)
        
        # Check if the error message appears
        self.assertContains(response, "Quantity exceeds available inventory.")
        
        # Verify that the inventory quantity remains unchanged
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, self.initial_quantity)
    
    def test_create_new_inventory_when_none_exists(self):
        # Log in the user
        self.client.login(username="testuser", password="password123")
        
        # Prepare the POST data for a valid transfer
        transfer_quantity = 20
        post_data = {
            'inventory_item': self.product.id,
            'quantity': transfer_quantity,
            'stock_location': "B2",  # Different stock location
            'stock_loc_level': "2"  # Different stock level
        }
        
        # Submit the POST request
        response = self.client.post(reverse('transfer_inventory'), post_data)
        
        # Check if the new inventory object is created
        new_inventory = Inventory.objects.get(
            product=self.product,
            distribution_center=self.center,
            stock_location="B2",
            stock_loc_level="2"
        )
        
        self.assertEqual(new_inventory.quantity, transfer_quantity)
        
        # Check if the success message is displayed
        self.assertContains(response, "Inventory transferred successfully.")

    def test_increment_inventory_quantity_when_exists(self):
        # Log in the user
        self.client.login(username="testuser", password="password123")
        
        # Prepare the POST data for a valid transfer (same stock location and level as existing inventory)
        transfer_quantity = 15
        post_data = {
            'inventory_item': self.product.id,
            'quantity': transfer_quantity,
            'stock_location': "A1",
            'stock_loc_level': "1"
        }
        
        # Submit the POST request
        response = self.client.post(reverse('transfer_inventory'), post_data)
        
        # Check if the existing inventory object's quantity is updated
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, self.initial_quantity + transfer_quantity)
        
        # Check if the success message is displayed
        self.assertContains(response, "Inventory quantity updated successfully.")
    
    def test_invalid_form_data(self):
        # Log in the user
        self.client.login(username="testuser", password="password123")
        
        # Submit invalid data (e.g., negative quantity)
        post_data = {
            'inventory_item': self.product.id,
            'quantity': -10,  # Invalid quantity
            'stock_location': "A1",
            'stock_loc_level': "1"
        }
        
        # Submit the POST request
        response = self.client.post(reverse('transfer_inventory'), post_data)
        
        # Check for form errors
        self.assertFormError(response, 'form', 'quantity', 'Ensure this value is greater than or equal to 0.')
        
        # Ensure the inventory quantity remains unchanged
        self.inventory.refresh_from_db()
        self.assertEqual(self.inventory.quantity, self.initial_quantity)


# Create your tests here.
