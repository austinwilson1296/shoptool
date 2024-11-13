from django.utils import timezone
from .models import TransactionHistory

def record_transaction(action, inventory_item, quantity, user, notes=""):
    # Get the user's profile and distribution center
    user_profile = user.userprofile  # Retrieves the related UserProfile instance
    user_center = user_profile.distribution_center.name if user_profile.distribution_center else "N/A"

    # Create the transaction history record
    TransactionHistory.objects.create(
        action=action,
        inventory_item=inventory_item,
        quantity=quantity,
        user=user,
        user_center=user_center,  # Store the center name or ID if needed
        notes=notes
    )