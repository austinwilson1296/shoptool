from django.contrib import admin
from django.contrib.auth.models import User
from .models import *

from import_export.admin import ImportExportModelAdmin


class UserProfileInLine(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class UserAdmin(admin.ModelAdmin):
    inlines = (UserProfileInLine,)




admin.site.unregister(User)
admin.site.register(User,UserAdmin)
admin.site.register(Product, ImportExportModelAdmin)
admin.site.register(Vendor)
admin.site.register(Center)
admin.site.register(Inventory, ImportExportModelAdmin)
admin.site.register(Checkout)
admin.site.register(CheckedOutBy)


