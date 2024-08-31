from django.contrib import admin

from .models import *

from import_export.admin import ImportExportModelAdmin


admin.site.register(Product, ImportExportModelAdmin)
admin.site.register(Vendor)
admin.site.register(Center)
admin.site.register(Inventory, ImportExportModelAdmin)
admin.site.register(Checkout)
admin.site.register(CheckedOutBy)


