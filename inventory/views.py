import csv
import pandas as pd
import random
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from io import StringIO
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse,JsonResponse,HttpResponseForbidden
from django.core.exceptions import ValidationError
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.template import Context,Engine
from django.template.loader import render_to_string
from .forms import CheckoutForm, ProductForm, FilteredCheckoutForm,TransferForm,InventoryLookup
from .models import Inventory, Product, Checkout, CheckedOutBy, Center,Vendor,UserProfile
from .utils import record_transaction


class HomePageView(LoginRequiredMixin, ListView):
    model = Inventory
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        # Get the default context from the parent class
        context = super().get_context_data(**kwargs)
        # Add the center quantities to the context
        context['center_quantities'] = self.distribution_center_summary()
        return context

    def distribution_center_summary(self):
        centers = Center.objects.all()
        center_quantities = {}

        for center in centers:
            filtered_inventory = Inventory.objects.filter(distribution_center=center)

            # Calculate total quantity
            total_quantity = filtered_inventory.aggregate(total_quantity=Sum('quantity'))

            # Calculate total cost by multiplying the quantity with the product's cost
            total_cost = filtered_inventory.aggregate(
                total_cost=Sum(F('quantity') * F('product__cost'), output_field=FloatField())
            )

            center_quantities[center.name] = {
                'total_quantity': total_quantity['total_quantity'] if total_quantity['total_quantity'] is not None else 0,
                'total_cost': total_cost['total_cost'] if total_cost['total_cost'] is not None else 0
            }

        return center_quantities

class ProductDetailView(LoginRequiredMixin,DetailView):
    model = Product
    template_name = "product_lookup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()

        inventory_items = Inventory.objects.filter(product=product)

        context["inventory_items"] = inventory_items

        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Inventory
    template_name = "product_create.html"
    form_class = ProductForm
    success_url = reverse_lazy('product_create')

    def get_initial(self):
        """
        Initialize the form with the distribution center from the user's profile.
        """
        initial = super().get_initial()
        user_center = self.request.user.userprofile.distribution_center
        initial['distribution_center'] = user_center  # Provide the user's center as initial data
        return initial

    def form_valid(self, form):
        # Extract form data
        distribution_center = form.cleaned_data['distribution_center']
        product = form.cleaned_data['product']
        quantity = form.cleaned_data['quantity']
        stock_location = form.cleaned_data['stock_location']
        stock_loc_level = form.cleaned_data['stock_loc_level']
        user = self.request.user
        user_center = user.userprofile.distribution_center

        # Check if the user is authorized to add to this distribution center
        if distribution_center != user_center:
            form.add_error('distribution_center', ValidationError(
                "You are not authorized to perform this action in this distribution center."
            ))
            return self.form_invalid(form)

        # Check if an existing inventory record exists
        existing_inventory = Inventory.objects.filter(
            distribution_center=distribution_center,
            product=product,
            stock_location=stock_location,
            stock_loc_level=stock_loc_level
        ).first()

        if existing_inventory:
            # Update the quantity of the existing inventory
            existing_inventory.quantity += quantity
            existing_inventory.save()

            # Record the transaction as a receiving action
            record_transaction(
                action='receive',
                inventory_item=existing_inventory,
                quantity=quantity,
                user=user,
                notes=f"Received {quantity} units of {product.name} at {distribution_center.name}."
            )
            messages.success(self.request, f"Processed Inventory Successfully Product Name:{product} | Quantity:{quantity} | Location:{stock_location}")
            return redirect(self.success_url)  # Redirect to success URL after updating
        else:
            # If no existing inventory record, save the new form to create it
            self.object = form.save()

            # Record the transaction as a receiving action for the new inventory item
            record_transaction(
                action='receive',
                inventory_item=self.object,
                quantity=quantity,
                user=user,
                notes=f"Created new inventory with {quantity} units of {product.name} at {distribution_center.name}."
            )
            return super().form_valid(form)  # Call the parent class's form_valid method

    def form_invalid(self, form):
        # Optionally handle invalid form submission
        return super().form_invalid(form)


@login_required
def checkout_inventory_view(request):
    user_center = request.user.userprofile.distribution_center  # Get the user’s distribution center
    user_center_str = str(user_center.storis_Abbreviation)  # Get the abbreviation for the center

    # If the user doesn't have a valid distribution center assigned
    if not user_center:
        messages.error(request, "No distribution center found for your profile.")
        return redirect('error_page')  # Redirect to an error page or some fallback page

    if request.method == "POST":
        form = CheckoutForm(request.POST, dc=user_center_str)  # Pass the abbreviation to the form

        if form.is_valid():
            center = form.cleaned_data['center']
            item = form.cleaned_data['inventory_item']
            quantity_checkout = form.cleaned_data['quantity']
            checked_out_by = form.cleaned_data['checked_out_by']
            
            # Validate that the user is allowed to check out from the given center
            if user_center_str == str(center):
                # Check if the requested quantity is available in inventory
                if quantity_checkout <= item.quantity:
                    item.quantity -= quantity_checkout
                    item.save()  # Update the inventory item quantity
                    Checkout.objects.create(
                        inventory_item=item,
                        checked_out_by=checked_out_by,  # Assuming CheckedOutBy is linked to UserProfile
                        checkout_date=datetime.now(),
                        quantity=quantity_checkout,
                        user=request.user
                    )
                    # Record the checkout transaction (similar to the transfer)
                    record_transaction(
                        action='checkout',
                        inventory_item=item,
                        quantity=quantity_checkout,
                        user=request.user,
                        notes=f"Checked out {quantity_checkout} units of {item}."
                    )

                    messages.success(request, 'Inventory checked out successfully.')
                    return redirect('checkout_create')  # Redirect to the checkout page or success URL
                else:
                    form.add_error('quantity', 'Insufficient inventory for the selected item.')
                    messages.error(request, 'Quantity exceeds available inventory.')
            else:
                messages.error(request, 'You do not have access to this DC.')
        else:
            messages.error(request, 'There was an error with the form.')

    else:
        form = CheckoutForm(dc=user_center_str)  # Initialize the form with the center abbreviation

    return render(request, 'checkout_create.html', {'form': form})
    
    
def load_checked_out_by(request):
    center_id = request.GET.get('center_id')
    checked_out_by = CheckedOutBy.objects.filter(distribution_center_id=center_id).order_by('name')
    data = [{'id': obj.id, 'name': obj.name} for obj in checked_out_by]
    return JsonResponse(data, safe=False)


@login_required
def get_inventory_items(request):
    center_id = request.GET.get('center')
    if center_id:
        # Fetch the inventory items with additional fields
        inventory_items = Inventory.objects.filter(distribution_center_id=center_id).values(
            'id',
            'product__name',
            'stock_location',
            'stock_loc_level',
            'quantity'
        )
          
        return JsonResponse({'items': list(inventory_items)})
    return JsonResponse({'items': []})


@login_required
def supply_levels(request, abbreviation):
    # Fetch the center based on abbreviation
    center = get_object_or_404(Center, storis_Abbreviation=abbreviation)

    # Aggregate total quantities for each product in the specified center
    product_totals = Inventory.objects.filter(distribution_center=center) \
        .values('product') \
        .annotate(total_quantity=Sum('quantity'))

    # Get unique product IDs from the aggregated results
    product_ids = [item['product'] for item in product_totals]

    # Fetch products with vendor information and map their safety stock and min_order_qty
    products = Product.objects.select_related('vendor').filter(id__in=product_ids)
    safety_stock_dict = {product.id: product.safety_stock for product in products}


    # Initialize a dictionary to aggregate product data by product ID
    product_data_dict = {}

    for item in product_totals:
        product_id = item['product']

        if product_id not in product_data_dict:
            product = Product.objects.get(id=product_id)
            product_data_dict[product_id] = {
                'product': product,
                'vendor': product.vendor,  # Add vendor information
                'total_quantity': item['total_quantity'],
                'safety_stock': safety_stock_dict[product_id],
                'total_cost': product.cost * item['total_quantity'],
                'amount_order':safety_stock_dict[product_id]-item['total_quantity'],
                'status': 'Sufficient' if item['total_quantity'] >= safety_stock_dict[product_id] else 'Insufficient',
                'order_cost': product.cost * (safety_stock_dict[product_id]-item['total_quantity']),
            }
        else:
            # Aggregate quantities for existing products
            product_data_dict[product_id]['total_quantity'] += item['total_quantity']
            product_data_dict[product_id]['status'] = 'Sufficient' if product_data_dict[product_id]['total_quantity'] >= product_data_dict[product_id]['safety_stock'] else 'Insufficient'

    # Convert the dictionary to a list of values
    product_data = list(product_data_dict.values())

    # Get all vendors for the filter dropdown
    vendors = Vendor.objects.all()

    # Filter by vendor if selected
    selected_vendor_id = request.GET.get('vendor')
    if selected_vendor_id:
        product_data = [data for data in product_data if data['vendor'].id == int(selected_vendor_id)]

    # Filter by insufficient status if selected
    show_insufficient = request.GET.get('insufficient')
    if show_insufficient:
        product_data = [data for data in product_data if data['status'] == 'Insufficient']

    # Check if the request is for exporting CSV
    if 'export' in request.GET:
        # Generate CSV file
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['Product', 'Vendor', 'Total Quantity', 'Safety Stock', 'Status','Order Amount','Order Cost'])
        for item in product_data:
            if item['total_quantity'] < item['safety_stock']:
                csv_writer.writerow([
                    item['product'].name,
                    item['vendor'].name,
                    item['total_quantity'],
                    item['safety_stock'],
                    item['status'],
                    item['amount_order'],
                    item['order_cost'],
                ])
        csv_file = csv_buffer.getvalue()

        csv_buffer.seek(0)  # Move to the start of the StringIO buffer
        df = pd.read_csv(csv_buffer)

        # Sort DataFrame (e.g., by 'Total Quantity')
        df_sorted = df.sort_values(by='Vendor', ascending=False)  # Adjust column name and order as needed

        # Write sorted DataFrame to a new buffer
        sorted_csv_buffer = StringIO()
        df_sorted.to_csv(sorted_csv_buffer, index=False)

        # Get the sorted CSV data
        sorted_csv_file = sorted_csv_buffer.getvalue()

        # Return CSV as response
        response = HttpResponse(sorted_csv_file, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Supply_Order_{center.name}.csv"'


        return response

    context = {
        'center': center,
        'product_data': product_data,
        'vendors': vendors,  # Pass vendors to the template
        'show_insufficient': show_insufficient,  # Pass insufficient filter status to the template
    }

    return render(request, 'inventory_comparison.html', context)

@login_required
def download_csv_report(request):
    # Query to get the total quantity, total cost by product name, person, and date
    checked_out_with_cost = (
        Checkout.objects
        .values('inventory_item__product__name', 'checked_out_by__name', 'checkout_date')
        .annotate(
            total_quantity=Sum('quantity'),
            total_cost=Sum(
                ExpressionWrapper(
                    F('quantity') * F('inventory_item__product__cost'),
                    output_field=FloatField()
                )
            )
        )
        .order_by('inventory_item__product__name', 'checked_out_by__name', 'checkout_date')
    )

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="checkout_report.csv"'

    writer = csv.writer(response)
    # Write the header row
    writer.writerow(['Product Name', 'Checked Out By', 'Date', 'Total Quantity', 'Total Cost'])

    # Write data rows
    for entry in checked_out_with_cost:
        writer.writerow([
            entry['inventory_item__product__name'],
            entry['checked_out_by__name'],
            entry['checkout_date'].strftime('%Y-%m-%d'),  # Format the date
            entry['total_quantity'],
            f"{entry['total_cost']:.2f}"  # Format the cost to two decimal places
        ])

    return response

def parse_date(date_str, format_str='%m/%d/%Y'):
    """Convert date string to datetime.date object based on the format."""
    try:
        return datetime.strptime(date_str, format_str).date()
    except ValueError:
        return None  # Return None if the date string is invalid


def random_color():
    """Generate a random color in hexadecimal format."""
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))


@login_required
def checkout_chart_view(request):
    # Get selected name and date range from query parameters
    selected_name = request.GET.get('name', '')
    start_date_str = request.GET.get('start_date', '')
    end_date_str = request.GET.get('end_date', '')

    # Parse the dates based on the format
    start_date = parse_date(start_date_str)
    end_date = parse_date(end_date_str)

    # Get distinct names for dropdown
    names = CheckedOutBy.objects.values_list('name', flat=True).distinct()

    # Build query filters
    filters = {}
    if selected_name:
        filters['checked_out_by__name'] = selected_name
    if start_date:
        filters['checkout_date__date__gte'] = start_date
    if end_date:
        filters['checkout_date__date__lte'] = end_date

    # Query the checkouts with filtering
    checkouts = Checkout.objects.filter(**filters).annotate(
        checkout_date_only=F('checkout_date__date'),
        product_name=F('inventory_item__product__name'),
        product_cost=F('inventory_item__product__cost')
    ).values(
        'checkout_date_only',
        'checked_out_by__name',
        'product_name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum(F('quantity') * F('product_cost'))
    ).order_by('checkout_date_only')

    # ------------------ Chart 1: Bar Chart of Quantities by Date ------------------
    unique_names = set(checkout['checked_out_by__name'] for checkout in checkouts)
    fig_quantity = go.Figure()

    for name in unique_names:
        name_checkouts = [c for c in checkouts if c['checked_out_by__name'] == name]
        dates = [c['checkout_date_only'] for c in name_checkouts]
        quantities = [c['total_quantity'] for c in name_checkouts]

        fig_quantity.add_trace(go.Bar(
            x=dates,
            y=quantities,
            name=name
        ))

    fig_quantity.update_layout(
        xaxis_title='Date',
        yaxis_title='Quantity',
        title='Checkout Quantity by Date',
        barmode='stack',
        legend_title='Names'
    )
    chart_quantity_html = fig_quantity.to_html(full_html=False)

    # ------------------ Chart 2: Table of Costs and Percentages ------------------
    names_list = list(unique_names)
    total_costs = [
        sum(c['total_cost'] for c in checkouts if c['checked_out_by__name'] == name)
        for name in names_list
    ]
    grand_total_cost = sum(total_costs)
    percentages = [
        (cost / grand_total_cost) * 100 if grand_total_cost > 0 else 0
        for cost in total_costs
    ]

    # Sort by total cost in descending order
    data = sorted(
        zip(names_list, total_costs, percentages),
        key=lambda x: x[1],  # Sort by total cost
        reverse=True  # Descending order
    )
    sorted_names, sorted_costs, sorted_percentages = zip(*data)

    fig_table = go.Figure(data=[
        go.Table(
            header=dict(
                values=["Name", "Total Cost", "Percentage of Total"],
                fill_color='paleturquoise',
                align='left'
            ),
            cells=dict(
                values=[
                    sorted_names,
                    sorted_costs,
                    [f"{p:.2f}%" for p in sorted_percentages]
                ],
                fill_color='lavender',
                align='left'
            )
        )
    ])
    chart_table_html = fig_table.to_html(full_html=False)

    # ------------------ Chart 3: Most Frequently Checked-Out Items ------------------
    product_data = (
        Checkout.objects.filter(**filters)
        .annotate(product_name=F('inventory_item__product__name'))
        .values('product_name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:10]
    )
    
    product_names = [p['product_name'] for p in product_data]
    product_quantities = [p['total_quantity'] for p in product_data]

    fig_items = go.Figure(data=[
        go.Bar(
            x=product_names,
            y=product_quantities,
            marker_color='skyblue'
        )
    ])
    fig_items.update_layout(
        xaxis_title='Product Name',
        yaxis_title='Total Quantity',
        title='Most Frequently Checked-Out Items',
        xaxis=dict(tickangle=45)
    )
    chart_items_html = fig_items.to_html(full_html=False)

    # ------------------ Render Template ------------------
    return render(request, 'checkout_chart.html', {
        'chart_quantity_html': chart_quantity_html,
        'chart_table_html': chart_table_html,
        'chart_items_html': chart_items_html,
        'names': names,
        'selected_name': selected_name,
        'start_date': start_date_str,
        'end_date': end_date_str
    })

#TO-DO - Add views for transferring inventory between storage locations.(BIN2BIN)
'''
1. Select item to transfer along with DC 
2.Enter quantity to transfer 
3.Location to transfer to.

REQUIREMENTS:
- Form that displays all inventory for a given location.
- Quantity to subtract from/add to selected location (along with product_name)
- List of locations in the available DC 
'''
@login_required
def transfer_inventory_view(request):
    # Get the user's distribution center abbreviation (string) for dropdown population
    user_center = request.user.userprofile.distribution_center  # This should be a Center instance
    user_center_str = str(user_center.storis_Abbreviation)

    # If the user doesn't have a valid distribution center assigned
    if not user_center:
        messages.error(request, "No distribution center found for your profile.")
        return redirect('error_page')  # Redirect to an error page or some fallback page

    if request.method == "POST":
        form = TransferForm(request.POST, dc=user_center_str)  # Pass the abbreviation string to the form

        if form.is_valid():
            item = form.cleaned_data['inventory_item']
            quantity_transfer = form.cleaned_data['quantity']
            stock_location = form.cleaned_data['stock_location']
            stock_location_level = form.cleaned_data['stock_loc_level']

            # Check if transfer quantity is not greater than available quantity
            if quantity_transfer <= item.quantity:
                # Decrease the quantity in the current inventory item
                item.quantity -= quantity_transfer
                item.save()

                # Record the transaction (transfer)
                record_transaction(
                    action='transfer',
                    inventory_item=item,
                    quantity=quantity_transfer,
                    user=request.user,
                    notes=f"Transferred {quantity_transfer} units of {item} to {stock_location} {stock_location_level}."
                )

                # Check if an Inventory object with the same product, location, level, and DC already exists
                existing_inventory = Inventory.objects.filter(
                    product=item.product,
                    distribution_center=user_center,
                    stock_location=stock_location,
                    stock_loc_level=stock_location_level
                ).first()

                if existing_inventory:
                    # If an existing inventory object is found, increment the quantity
                    existing_inventory.quantity += quantity_transfer
                    existing_inventory.save()
                    messages.success(request, 'Inventory quantity updated successfully.')
                else:
                    # If no matching inventory object is found, create a new one
                    new_inv_object = Inventory(
                        distribution_center=user_center,  # Use the actual Center instance
                        product=item.product,
                        quantity=quantity_transfer,
                        stock_location=stock_location,
                        stock_loc_level=stock_location_level
                    )
                    new_inv_object.save()
                    messages.success(request, 'Inventory transferred successfully.')

                return redirect('transfer_inventory')  # Redirect to the transfer inventory page (or success URL)
            else:
                form.add_error('quantity', 'Insufficient inventory for the selected item.')
                messages.error(request, 'Quantity exceeds available inventory.')
        else:
            messages.error(request, 'There was an error with the form.')
    else:
        form = TransferForm(dc=user_center_str)  # Pass the abbreviation string to the form

    return render(request, 'b2b.html', {'form': form})
#TO-DO - Add views for creating/viewing/receiving/completing transfers between locations.

#TO-DO - Inventory views for each storage location.

#TO-DO - Add view inside of the checkout and create views to show on hand items and where they currently are.

#TO-DO - Supply request forms. User auth not required. 

#TO-DO - Additional Analytics? Check out items and cost per team member | Top 10 most checked out items w cost. 

#TO-DO - Product in location lookup. 
@login_required
def inventory_lookup_view(request):
    # Get the user's associated distribution center
    user_center = request.user.userprofile.distribution_center  # Assuming this returns a Center instance
    user_center_str = str(user_center.storis_Abbreviation)

    items = []  # Default empty list for items
    sorted_items = []
    

    # Initialize the form, passing 'dc' as the user's center abbreviation
    form = InventoryLookup(dc=user_center_str)  # Use the user center abbreviation directly
    
    if request.method == "POST":
        form = InventoryLookup(request.POST, dc=user_center_str)  # Pass 'dc' to filter stock locations
        if form.is_valid():
            stock_location = form.cleaned_data['stock_location']
            # Filter Inventory based on selected stock location
            items = Inventory.objects.filter(stock_location=stock_location)
            sorted_items = items.order_by('stock_loc_level','product')
            

    return render(request, "inventory_lookup.html", {
        "form": form,
        "items": sorted_items,
    })
