import csv
import pandas as pd
import random
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from io import StringIO
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
from .forms import CheckoutForm, ProductForm, FilteredCheckoutForm,TransferForm
from .models import Inventory, Product, Checkout, CheckedOutBy, Center,Vendor,UserProfile


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
    success_url = reverse_lazy('home')

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

        user_center = self.request.user.userprofile.distribution_center

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
            return redirect(self.success_url)  # Redirect to success URL after updating
        else:
            # Proceed with creating a new record
            return super().form_valid(form)  # Call the parent class's form_valid method

    def form_invalid(self, form):
        # Optionally handle invalid form submission
        return super().form_invalid(form)


class CheckoutCreateView(LoginRequiredMixin,CreateView):
    model = Checkout
    form_class = CheckoutForm
    template_name = "checkout_create.html"
    success_url = reverse_lazy('checkout_create')

    def form_valid(self, form):
        # First, call the parent method to handle form saving
        form.instance.user = self.request.user
        response = super().form_valid(form)

            
        # Get the cleaned data from the form
        center = form.cleaned_data['center']
        inventory_item = form.cleaned_data['inventory_item']
        quantity = form.cleaned_data['quantity']
        
            
        # Update the inventory item quantity
        inventory_item = Inventory.objects.get(id=inventory_item.id)

        user_center = self.request.user.userprofile.distribution_center

        if center != user_center:
            form.add_error('center', ValidationError("You are not authorized to perform this action in this distribution center."))
            return self.form_invalid(form)
        
            
        if inventory_item.quantity >= quantity:
                inventory_item.quantity -= quantity
                inventory_item.save()
                
        else:
                form.add_error('quantity', 'Insufficient inventory for the selected item.')
                return self.form_invalid(form)

        return response

    def form_invalid(self, form):
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' not in context:
            context['form'] = self.get_form()
        return context
    
    
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

    # Query the checkouts with filtering based on the selected name and date range
    checkouts = Checkout.objects.filter(**filters).annotate(
        checkout_date_only=F('checkout_date__date'),
        product_cost=F('inventory_item__product__cost')
    ).values(
        'checkout_date_only',
        'checked_out_by__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_cost=Sum(F('quantity') * F('product_cost'))
    ).order_by('checkout_date_only')

    # Generate random colors for each unique name
    unique_names = set(checkout['checked_out_by__name'] for checkout in checkouts)
    color_map = {name: random_color() for name in unique_names}

    # Create the Plotly figure
    fig = go.Figure()

    # Add a bar chart trace for each name
    for name in unique_names:
        marker_color = color_map[name]
        name_checkouts = [c for c in checkouts if c['checked_out_by__name'] == name]
        dates = [c['checkout_date_only'] for c in name_checkouts]
        quantities = [c['total_quantity'] for c in name_checkouts]

        fig.add_trace(go.Bar(
            x=dates,
            y=quantities,
            name=name,
            marker_color=marker_color
        ))

    # Update layout
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Quantity',
        title='Checkout Quantity by Date',
        barmode='stack',
        legend_title='Names'
    )

    # Convert to HTML
    chart_html = fig.to_html(full_html=False)

    # Render the template with the chart and names
    return render(request, 'checkout_chart.html', {
        'chart_html': chart_html,
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
    user_center_str = str(request.user.userprofile.distribution_center.storis_Abbreviation)

    # Get the actual Center object for saving in the database
    user_center = request.user.userprofile.distribution_center  # This should be a Center instance

    if not user_center:
        # Handle the case where the user does not have a valid distribution center assigned
        messages.error(request, "No distribution center found for your profile.")
        return redirect('home')  # Redirect to an error page or some fallback page

    if request.method == "POST":
        form = TransferForm(request.POST, dc=user_center_str)  # Pass the abbreviation string to the form
        if form.is_valid():
            item = form.cleaned_data['inventory_item']
            quantity_transfer = form.cleaned_data['quantity']
            stock_location = form.cleaned_data['stock_location']
            stock_location_level = form.cleaned_data['stock_loc_level']

            # Check if transfer quantity is not greater than available quantity
            if quantity_transfer <= item.quantity:
                item.quantity -= quantity_transfer
                item.save()

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

                return redirect('transfer_inventory')  # Replace with your success URL name
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