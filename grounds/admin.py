from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html

from .models import Event, Ground, GroundSuggestion, GroundTip, Match, Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "league_level", "is_current_92")
    list_filter = ("league_level", "is_current_92")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "league_level", "is_current_92", "primary_colour")}),
        ("Assets", {"fields": ("shirt",)}),
    )


@admin.register(Ground)
class GroundAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "name", "team", "town_or_city", "capacity", "opened_year")
    list_filter = ("team__league_level",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "team__name", "town_or_city", "postcode")
    readonly_fields = ("image_preview",)
    fieldsets = (
        (None, {"fields": ("name", "slug", "team", "town_or_city", "postcode", "capacity", "opened_year", "image", "image_preview")}),
        ("Location", {"fields": ("latitude", "longitude")}),
        ("Away fans", {"fields": ("away_end", "away_entrance", "away_allocation")}),
        ("Guide", {"fields": ("address", "transport_notes", "parking_notes", "drinking_notes", "first_visit_tip", "info_updated_at")}),
    )

    @admin.display(description="Photo")
    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="height:36px; border-radius:4px;">', obj.image.url)
        return "—"

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height:200px; border-radius:8px;">', obj.image.url)
        return "No image uploaded"


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("__str__", "competition", "matchday", "kickoff", "status")
    list_filter = ("competition", "status", "matchday")
    search_fields = ("home_team__name", "away_team__name")
    date_hierarchy = "kickoff"
    ordering = ["-kickoff"]


def _approve_suggestions(modeladmin, request, queryset):
    for suggestion in queryset.filter(status=GroundSuggestion.Status.PENDING):
        suggestion.apply(reviewer=request.user)


_approve_suggestions.short_description = "Approve selected suggestions (writes to ground)"


def _reject_suggestions(modeladmin, request, queryset):
    queryset.filter(status=GroundSuggestion.Status.PENDING).update(
        status=GroundSuggestion.Status.REJECTED,
        reviewed_by=request.user,
        reviewed_at=timezone.now(),
    )


_reject_suggestions.short_description = "Reject selected suggestions"


@admin.register(GroundSuggestion)
class GroundSuggestionAdmin(admin.ModelAdmin):
    list_display = ("thumbnail", "ground", "field_name", "user", "status", "created_at")
    list_filter = ("status", "field_name")
    search_fields = ("ground__name", "user__username", "proposed_value")
    readonly_fields = ("ground", "user", "field_name", "proposed_value", "image_preview", "created_at")
    actions = [_approve_suggestions, _reject_suggestions]
    ordering = ["-created_at"]
    change_list_template = "admin/grounds/suggestion_change_list.html"

    @admin.display(description="")
    def thumbnail(self, obj):
        if obj.proposed_image:
            return format_html('<img src="{}" style="height:32px; border-radius:4px;">', obj.proposed_image.url)
        return ""

    @admin.display(description="Proposed image")
    def image_preview(self, obj):
        if obj.proposed_image:
            return format_html('<img src="{}" style="max-height:240px; border-radius:8px;">', obj.proposed_image.url)
        return "—"

    def get_urls(self):
        urls = [
            path("dashboard/", staff_member_required(suggestions_dashboard), name="grounds_suggestions_dashboard"),
        ]
        return urls + super().get_urls()


def _approve_tips(modeladmin, request, queryset):
    queryset.update(is_approved=True)


_approve_tips.short_description = "Approve selected tips"


@admin.register(GroundTip)
class GroundTipAdmin(admin.ModelAdmin):
    list_display = ("ground", "category", "user", "is_approved", "created_at")
    list_filter = ("is_approved", "category")
    search_fields = ("ground__name", "user__username", "body")
    readonly_fields = ("ground", "user", "category", "body", "created_at")
    actions = [_approve_tips]
    ordering = ["-created_at"]
    change_list_template = "admin/grounds/suggestion_change_list.html"


def suggestions_dashboard(request):
    pending_suggestions = (
        GroundSuggestion.objects.filter(status=GroundSuggestion.Status.PENDING)
        .select_related("ground", "user")
        .order_by("-created_at")
    )
    pending_tips = (
        GroundTip.objects.filter(is_approved=False)
        .select_related("ground", "user")
        .order_by("-created_at")
    )
    suggestions_by_field = (
        pending_suggestions.values("field_name").annotate(n=Count("id")).order_by("-n")
    )
    tips_by_category = (
        pending_tips.values("category").annotate(n=Count("id")).order_by("-n")
    )
    field_labels = dict(GroundSuggestion.FieldName.choices)
    category_labels = dict(GroundTip.Category.choices)

    context = {
        **admin.site.each_context(request),
        "title": "Suggestions dashboard",
        "pending_suggestions": pending_suggestions[:25],
        "pending_tips": pending_tips[:25],
        "suggestions_by_field": [
            {"label": field_labels.get(row["field_name"], row["field_name"]), "count": row["n"]}
            for row in suggestions_by_field
        ],
        "tips_by_category": [
            {"label": category_labels.get(row["category"], row["category"]), "count": row["n"]}
            for row in tips_by_category
        ],
        "total_pending_suggestions": pending_suggestions.count(),
        "total_pending_tips": pending_tips.count(),
    }
    return render(request, "admin/grounds/suggestions_dashboard.html", context)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "user", "ground", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__username", "ground__name")
    readonly_fields = ("event_type", "user", "ground", "context", "created_at")
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    change_list_template = "admin/grounds/event_change_list.html"

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        urls = [
            path("dashboard/", staff_member_required(events_dashboard), name="grounds_events_dashboard"),
        ]
        return urls + super().get_urls()


def events_dashboard(request):
    types = Event.Type.choices  # [(value, label), ...]
    type_values = [v for v, _ in types]
    type_labels = [lbl for _, lbl in types]

    since = timezone.now() - timedelta(days=30)
    rows = (
        Event.objects.filter(created_at__gte=since)
        .annotate(day=TruncDate("created_at"))
        .values("day", "event_type")
        .annotate(n=Count("id"))
    )
    by_day: dict = {}
    for r in rows:
        by_day.setdefault(r["day"], {})[r["event_type"]] = r["n"]
    daily = [
        {
            "day": day,
            "counts": [by_day[day].get(v, 0) for v in type_values],
            "total": sum(by_day[day].values()),
        }
        for day in sorted(by_day, reverse=True)
    ]

    totals_all = {
        r["event_type"]: r["n"]
        for r in Event.objects.values("event_type").annotate(n=Count("id"))
    }
    totals = [{"label": lbl, "value": totals_all.get(val, 0)} for val, lbl in types]

    context = {
        **admin.site.each_context(request),
        "title": "Events dashboard",
        "type_labels": type_labels,
        "daily": daily,
        "totals": totals,
        "grand_total": Event.objects.count(),
        "last_30_total": sum(d["total"] for d in daily),
    }
    return render(request, "admin/grounds/events_dashboard.html", context)
