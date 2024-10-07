from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin
from django.contrib.auth.models import User
from .models import *
from import_export.admin import ImportExportModelAdmin

class UserProfileInLine(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

# Extend the default UserAdmin to retain password hashing and other functionality
class UserAdmin(DefaultUserAdmin):  
    inlines = (UserProfileInLine,)

# Unregister the default User model and register the new UserAdmin with inline profile
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Register other models
admin.site.register(Product, ImportExportModelAdmin)
admin.site.register(Vendor)
admin.site.register(Center)
admin.site.register(Inventory, ImportExportModelAdmin)
admin.site.register(Checkout)
admin.site.register(CheckedOutBy)



