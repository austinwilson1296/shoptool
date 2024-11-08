# forms.py
from django import forms
from django.db import transaction
from .models import Checkout, Inventory, CheckedOutBy,Center,UserProfile


class CheckoutForm(forms.ModelForm):
    center = forms.ModelChoiceField(
        queryset=Center.objects.all(),
        empty_label="Select Center"
    )
    checked_out_by = forms.ModelChoiceField(
        queryset=CheckedOutBy.objects.none(),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'select2'})  # Add 'select2' class
    )
    inventory_item = forms.ModelChoiceField(
        queryset=Inventory.objects.none(),
        empty_label=None,
        widget=forms.Select(attrs={'class': 'select2'})  # Add 'select2' class
    )

    class Meta:
        model = Checkout
        fields = ['center', 'inventory_item', 'checked_out_by', 'quantity']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Handle cases when form data is submitted with a selected center
        if 'center' in self.data:
            try:
                center_id = int(self.data.get('center'))
                # Set queryset for checked_out_by based on selected center
                self.fields['checked_out_by'].queryset = CheckedOutBy.objects.filter(distribution_center_id=center_id)
                # Set queryset for inventory_item based on selected center
                self.fields['inventory_item'].queryset = Inventory.objects.filter(distribution_center_id=center_id)
            except (ValueError, TypeError):
                # Set empty querysets if center_id is invalid
                self.fields['checked_out_by'].queryset = CheckedOutBy.objects.none()
                self.fields['inventory_item'].queryset = Inventory.objects.none()

        # When editing an existing instance (like a saved Checkout record)
        elif self.instance.pk:
            center_id = self.instance.center.id
            # Set checked_out_by and inventory_item querysets based on instance's center
            self.fields['checked_out_by'].queryset = CheckedOutBy.objects.filter(distribution_center_id=center_id)
            self.fields['inventory_item'].queryset = Inventory.objects.filter(distribution_center_id=center_id)
        else:
            # Default to empty querysets when no center is selected
            self.fields['checked_out_by'].queryset = CheckedOutBy.objects.none()
            self.fields['inventory_item'].queryset = Inventory.objects.none()



class ProductForm(forms.ModelForm):
    CABINET_CHOICES = [
        ('XCAB1', 'XCAB 1 – Sprays'),
        ('XCAB1', 'XCAB 1 (Four Oaks) – Sprays'),
        ('XCAB2', 'XCAB 2 – Sprays'),
        ('XCAB3', 'XCAB 3 – Sprays'),
        ('XCAB4', 'XCAB 4 – Sprays'),
        ('XCAB5', 'XCAB 5 – Tools/bits'),
        ('XCAB6', 'XCAB 6 – Bondo/Cleaning sprays'),
        ('XCAB7', 'XCAB 7 – Sandpaper'),
        ('XCAB8', 'XCAB 8 – Gloves/Masking tape'),
        ('XCAB9', 'XCAB 9 – Fillsticks/markers/small touch up'),
        ('QIS', 'QIS – Total Packaging/Atlantic Purchases'),
        ('Fastenal', 'Fastenal Purchases'),
    ]

    LEVEL_CHOICES = [
        ('LEVEL1', 'Level 1'),
        ('LEVEL2', 'Level 2'),
        ('LEVEL3', 'Level 3'),
        ('LEVEL4', 'Level 4'),
        ('LEVEL5', 'Level 5'),
        ('LEVEL6', 'Level 6'),
    ]

    stock_location = forms.ChoiceField(choices=CABINET_CHOICES)
    stock_loc_level = forms.ChoiceField(choices=LEVEL_CHOICES)

    class Meta:
        model = Inventory
        fields = ['distribution_center', 'product', 'quantity', 'stock_location', 'stock_loc_level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply the select2 class to the product field
        self.fields['product'].widget.attrs.update({'class': 'select2'})

        # You can also apply select2 to other fields if needed
        self.fields['stock_location'].widget.attrs.update({'class': 'select2'})
        self.fields['stock_loc_level'].widget.attrs.update({'class': 'select2'})

class FilteredCheckoutForm(forms.Form):
    checked_out_by = forms.ModelChoiceField(
        queryset=CheckedOutBy.objects.all(),
        required=False,  # Allows for no selection
        empty_label="Select Name",
        widget=forms.Select(attrs={'class': 'form-control select2'}),  # Explicitly set widget
        label="Filter by Name"  # Label for the dropdown
    )