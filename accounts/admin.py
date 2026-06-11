from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("The 92 profile", {"fields": ("birthday", "favourite_team")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("The 92 profile", {"fields": ("email", "birthday", "favourite_team")}),
    )
    list_display = ("username", "email", "favourite_team", "is_staff", "is_active")
    list_filter = UserAdmin.list_filter + ("favourite_team",)
