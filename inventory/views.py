import csv
import pandas as pd
import operator
import plotly.graph_objects as go
import plotly.express as px
from io import StringIO
from django.shortcuts import render,redirect, get_object_or_404
from django.http import HttpResponse
from django.views.generic import ListView, DetailView
from django.views.generic.edit import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, F, FloatField, ExpressionWrapper
from django.template import Context,Engine
from django.template.loader import render_to_string
from .forms import CheckoutForm, ProductForm, FilteredCheckoutForm
from .models import Inventory, Product, Checkout, CheckedOutBy, Center,Vendor


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

class ProductDetailView(DetailView):
    model = Product
    template_name = "product_lookup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()

        inventory_items = Inventory.objects.filter(product=product)

        context["inventory_items"] = inventory_items

        return context


class ProductCreateView(CreateView):
    model = Inventory
    template_name = "product_create.html"
    form_class = ProductForm
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        # Extract form data
        distribution_center = form.cleaned_data['distribution_center']
        product = form.cleaned_data['product']
        quantity = form.cleaned_data['quantity']
        stock_location = form.cleaned_data['stock_location']
        stock_loc_level = form.cleaned_data['stock_loc_level']

        # Find existing inventory record
        existing_inventory = Inventory.objects.filter(
            distribution_center=distribution_center,
            product=product,
            stock_location=stock_location,
            stock_loc_level=stock_loc_level
        ).first()  # Retrieve the first matching record or None

        if existing_inventory:
            # Update the existing record's quantity
            existing_inventory.quantity += quantity
            existing_inventory.save()
            return redirect(self.success_url)  # Redirect to success URL after updating
        else:
            # Create a new record if none exists
            return super().form_valid(form)  # Call the parent class's form_valid method

    def form_invalid(self, form):
        # Handle invalid form submission if needed
        return super().form_invalid(form)


class CheckoutCreateView(CreateView):
    model = Checkout
    form_class = CheckoutForm
    template_name = "checkout_create.html"
    success_url = reverse_lazy('checkout_create')

    def form_valid(self, form):
        # The form's save method handles the transaction and updates
        return super().form_valid(form)

    def form_invalid(self, form):
        # Handle form errors
        return super().form_invalid(form)


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
        response = HttpResponse(csv_file, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="Supply_Order_{center.name}.csv"'


        return response

    context = {
        'center': center,
        'product_data': product_data,
        'vendors': vendors,  # Pass vendors to the template
        'show_insufficient': show_insufficient,  # Pass insufficient filter status to the template
    }

    return render(request, 'inventory_comparison.html', context)


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


def checkout_chart_view(request):
    # Get selected name from query parameters
    selected_name = request.GET.get('name', '')

    # Get distinct names for dropdown
    names = CheckedOutBy.objects.values_list('name', flat=True).distinct()

    # Query the checkouts with filtering based on the selected name
    if selected_name:
        checkouts = Checkout.objects.filter(
            checked_out_by__name=selected_name
        ).annotate(
            checkout_date_only=F('checkout_date__date'),
            product_cost=F('inventory_item__product__cost')
        ).values(
            'checkout_date_only',
            'checked_out_by__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_cost=Sum(F('quantity') * F('product_cost'))
        ).order_by('checkout_date_only')
    else:
        checkouts = Checkout.objects.annotate(
            checkout_date_only=F('checkout_date__date'),
            product_cost=F('inventory_item__product__cost')
        ).values(
            'checkout_date_only',
            'checked_out_by__name'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_cost=Sum(F('quantity') * F('product_cost'))
        ).order_by('checkout_date_only')

    # Generate a color palette based on the number of unique names
    unique_names = set(checkout['checked_out_by__name'] for checkout in checkouts)
    color_palette = px.colors.qualitative.Plotly[:len(unique_names)]
    color_map = dict(zip(unique_names, color_palette))

    # Create the Plotly figure
    fig = go.Figure()

    # Add a bar chart trace for each name
    for name in unique_names:
        name_checkouts = [c for c in checkouts if c['checked_out_by__name'] == name]
        dates = [c['checkout_date_only'] for c in name_checkouts]
        quantities = [c['total_quantity'] for c in name_checkouts]
        
        fig.add_trace(go.Bar(
            x=dates,
            y=quantities,
            name=name,
            marker_color=color_map[name]
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
        'selected_name': selected_name
    })