from django.contrib import admin

from .models import Ground, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "league_level", "is_current_92")
    list_filter = ("league_level", "is_current_92")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@admin.register(Ground)
class GroundAdmin(admin.ModelAdmin):
    list_display = ("name", "team", "town_or_city", "capacity", "opened_year")
    list_filter = ("team__league_level",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "team__name", "town_or_city", "postcode")
