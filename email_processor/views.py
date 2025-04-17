from django.shortcuts import render
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Order, Part

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# File handler for logging
file_handler = logging.FileHandler("parse.log")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)

@csrf_exempt  # Disable CSRF protection (only if necessary, use proper authentication)
def process_data(request):
    """
    Process data from Power Automate and store it in the database.
    """
    if request.method != "POST":
        logger.warning("Received a non-POST request")
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        data = json.loads(request.body)
        logger.info("Received request data: %s", data)

        order_info = data.get("body", {}).get("orderInfo", {})
        shipping_info = data.get("body", {}).get("shippingInfo", {})
        replacement_parts = data.get("body", {}).get("replacementParts", [])

        # Create Order instance
        order = Order.objects.create(
            purchase_order_number=order_info.get("purchaseOrderNumber"),
            ashley_order_number=order_info.get("ashleyOrderNumber"),
            ashley_model_number=order_info.get("ashleyModelNumber"),
            model_description=order_info.get("modelDescription"),
            shipping_method=shipping_info.get("shippingMethod"),
            tracking_number=shipping_info.get("trackingNumber"),
        )
        logger.info("Successfully added order: %s", order.purchase_order_number)

        # Create Part instances
        parts = [
            Part(
                part_number=entry.get("partNumber"),
                description=entry.get("partDescription"),
                quantity=entry.get("quantity"),
                order=order,
            )
            for entry in replacement_parts
        ]
        Part.objects.bulk_create(parts)  # Bulk insert for better performance
        logger.info("Successfully added %d parts to database", len(parts))

        return JsonResponse({"message": "Success", "status": "ok"}, status=200)

    except json.JSONDecodeError:
        logger.error("Invalid JSON data received", exc_info=True)
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)
        return JsonResponse({"error": str(e)}, status=500)


