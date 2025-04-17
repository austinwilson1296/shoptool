from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import *
# Register your models here.


admin.site.register(Order, ImportExportModelAdmin)
admin.site.register(Part, ImportExportModelAdmin)
