from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AppUser, Setting


@admin.register(AppUser)
class AppUserAdmin(UserAdmin):
    model = AppUser
    list_display = ("login", "role", "is_active", "is_staff")
    ordering = ("login",)
    fieldsets = (
        (None, {"fields": ("login", "password")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
        ("Info", {"fields": ("role",)}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("login", "password1", "password2", "role"),
            },
        ),
    )
    search_fields = ("login",)


@admin.register(Setting)
class SettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)
