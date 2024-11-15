# forms.py
from django import forms
from .models import Checkout, Inventory, CheckedOutBy,Center,UserProfile
from .locations import *




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
        dc = kwargs.pop('dc', None)  # Get the passed distribution center abbreviation
        super().__init__(*args, **kwargs)
        for key,value in self.data.items():
            print(key,value)
        # Set initial value for center from the user’s profile
        if dc:
            try:
                user_center = Center.objects.get(storis_Abbreviation=dc)
                
                self.fields['center'].initial = user_center
            except Center.DoesNotExist:
                pass  # No center for the user

            # If 'center' is passed in the data, update the dependent fields (checked_out_by, inventory_item)
            if 'center' in self.data:
                center_id = self.data.get('center')
                
                self.fields['checked_out_by'].queryset = CheckedOutBy.objects.filter(distribution_center_id=center_id)
                self.fields['inventory_item'].queryset = Inventory.objects.filter(distribution_center_id=center_id).exclude(quantity=0)

            # Handle dynamic queryset for editing an existing Checkout instance
        elif self.instance.pk:
            center_id = self.instance.center.id
            self.fields['checked_out_by'].queryset = CheckedOutBy.objects.filter(distribution_center_id=center_id)
            self.fields['inventory_item'].queryset = Inventory.objects.filter(distribution_center_id=center_id).exclude(quantity=0)
        else:
            self.fields['checked_out_by'].queryset = CheckedOutBy.objects.none()
            self.fields['inventory_item'].queryset = Inventory.objects.none()



class ProductForm(forms.ModelForm):
    # Fields with choices initialized to empty since they are set dynamically in __init__
    stock_location = forms.ChoiceField(choices=[])
    stock_loc_level = forms.ChoiceField(choices=LEVEL_CHOICES)

    class Meta:
        model = Inventory
        fields = ['distribution_center', 'product', 'quantity', 'stock_location', 'stock_loc_level']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get the distribution center from initial data or context
        distribution_center = str(self.initial.get('distribution_center', None))
        
        # Debug print for verifying the distribution center value
        print(f"Distribution Center: {distribution_center}")

        # Check if distribution_center is provided and assign appropriate choices
        if distribution_center == '710':
            self.fields['stock_location'].choices = CABINET_CHOICES_710
        elif distribution_center == '730':
            self.fields['stock_location'].choices = CABINET_CHOICES_730
        elif distribution_center == '750':
            self.fields['stock_location'].choices = CABINET_CHOICES_750
        else:
            self.fields['stock_location'].choices = []

        # Apply select2 class to fields
        self.fields['product'].widget.attrs.update({'class': 'select2'})
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

class TransferForm(forms.Form):
    inventory_item = forms.ModelChoiceField(queryset=Inventory.objects.all(), label='Item to transfer')
    quantity = forms.IntegerField(min_value=1, label="Quantity to Transfer")
    stock_location = forms.ChoiceField(choices=[], label="Location to transfer to")
    stock_loc_level = forms.ChoiceField(choices=LEVEL_CHOICES, label="Level of receiving location")

    def __init__(self, *args, **kwargs):
        dc = kwargs.pop('dc', None)  # Expecting 'dc' to be passed in when initializing the form
        super().__init__(*args, **kwargs)
        
        # Filter inventory items based on the distribution center (dc)
        if dc:
            # Filter Inventory based on the distribution_center foreign key
            self.fields['inventory_item'].queryset = Inventory.objects.filter(distribution_center__storis_Abbreviation=dc)
        
        # Set choices for stock_location based on the distribution center
        if dc == '710':
            self.fields['stock_location'].choices = CABINET_CHOICES_710
        elif dc == '730':
            self.fields['stock_location'].choices = CABINET_CHOICES_730
        elif dc == '750':
            self.fields['stock_location'].choices = CABINET_CHOICES_750
        else:
            self.fields['stock_location'].choices = []

        # Apply select2 styling, if needed
        self.fields['inventory_item'].widget.attrs.update({'class': 'select2'})
        self.fields['stock_location'].widget.attrs.update({'class': 'select2'})
        self.fields['stock_loc_level'].widget.attrs.update({'class': 'select2'})



class InventoryLookup(forms.Form):
    stock_location = forms.ChoiceField(choices=[], label="Select Cabinet to Lookup")
    
    def __init__(self, *args, **kwargs):
        dc = kwargs.pop('dc', None)  # Distribution center passed in initialization
        super().__init__(*args, **kwargs)

        # Dynamically set choices for stock_location based on the provided dc
        if dc == '710':
            self.fields['stock_location'].choices = CABINET_CHOICES_710
        elif dc == '730':
            self.fields['stock_location'].choices = CABINET_CHOICES_730
        elif dc == '750':
            self.fields['stock_location'].choices = CABINET_CHOICES_750
        else:
            self.fields['stock_location'].choices = []

        # Apply select2 styling, if needed
        self.fields['stock_location'].widget.attrs.update({'class': 'select2'})
        
