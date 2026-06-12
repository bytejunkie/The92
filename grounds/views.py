from django.db.models import Case, IntegerField, Q, Value, When
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


VALID_LEAGUES = {c[0] for c in Team.LeagueLevel.choices}


def ground_list(request):
    league = request.GET.get("league", "").strip()
    q = request.GET.get("q", "").strip()

    grounds = Ground.objects.select_related("team").annotate(
        league_order=LEAGUE_ORDER
    ).order_by("league_order", "team__name")

    if league and league in VALID_LEAGUES:
        grounds = grounds.filter(team__league_level=league)
    else:
        league = ""

    if q:
        grounds = grounds.filter(
            Q(name__icontains=q) | Q(team__name__icontains=q)
        )

    context = {
        "grounds": grounds,
        "current_league": league,
        "current_q": q,
    }
    return render(request, "grounds/ground_list.html", context)


def ground_detail(request, slug):
    ground = get_object_or_404(Ground.objects.select_related("team"), slug=slug)
    return render(request, "grounds/ground_detail.html", {"ground": ground})
