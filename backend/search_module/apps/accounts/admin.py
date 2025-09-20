from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, LoginSession


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fields = ('role', 'cnic', 'advocate_license_number', 'full_name', 'phone_number', 'address')


class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'get_role', 'is_staff', 'date_joined')
    list_filter = ('profile__role', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    
    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, 'profile') else 'No Profile'
    get_role.short_description = 'Role'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'full_name', 'cnic', 'advocate_license_number', 'created_at')
    list_filter = ('role', 'created_at')
    search_fields = ('user__username', 'user__email', 'full_name', 'cnic', 'advocate_license_number')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'ip_address', 'is_active', 'logout_time')
    list_filter = ('is_active', 'login_time')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('login_time',)


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
