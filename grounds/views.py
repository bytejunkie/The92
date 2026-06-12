from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, render

from .models import Ground, Team

LEAGUE_ORDER = Case(
    When(team__league_level=Team.LeagueLevel.PREMIER_LEAGUE, then=Value(1)),
    When(team__league_level=Team.LeagueLevel.CHAMPIONSHIP, then=Value(2)),
    When(team__league_level=Team.LeagueLevel.LEAGUE_ONE, then=Value(3)),
    When(team__league_level=Team.LeagueLevel.LEAGUE_TWO, then=Value(4)),
    default=Value(5),
    output_field=IntegerField(),
)


def home(request):
    grounds = Ground.objects.select_related("team").annotate(
        league_order=LEAGUE_ORDER
    ).order_by("league_order", "team__name")[:3]
    context = {
        "grounds": grounds,
        "visited_count": 57,
        "total_count": 92,
        "friends_count": 248,
    }
    return render(request, "grounds/home.html", context)


def ground_list(request):
    grounds = Ground.objects.select_related("team").annotate(
        league_order=LEAGUE_ORDER
    ).order_by("league_order", "team__name")
    return render(request, "grounds/ground_list.html", {"grounds": grounds})


def ground_detail(request, slug):
    ground = get_object_or_404(Ground.objects.select_related("team"), slug=slug)
    return render(request, "grounds/ground_detail.html", {"ground": ground})
