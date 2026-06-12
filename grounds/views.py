from datetime import date

from django.contrib.auth.decorators import login_required
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render

from .models import Ground, Team, Visit

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
    visited_count = 0
    if request.user.is_authenticated:
        visited_count = (
            Visit.objects.filter(user=request.user, visit_type=Visit.VisitType.VISITED)
            .values("ground")
            .distinct()
            .count()
        )
    context = {
        "grounds": grounds,
        "visited_count": visited_count,
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

    visited_ground_ids = set()
    if request.user.is_authenticated:
        visited_ground_ids = set(
            Visit.objects.filter(
                user=request.user, visit_type=Visit.VisitType.VISITED
            ).values_list("ground_id", flat=True).distinct()
        )

    context = {
        "grounds": grounds,
        "current_league": league,
        "current_q": q,
        "visited_ground_ids": visited_ground_ids,
    }
    return render(request, "grounds/ground_list.html", context)


def ground_detail(request, slug):
    ground = get_object_or_404(Ground.objects.select_related("team"), slug=slug)
    user_has_visited = (
        request.user.is_authenticated
        and ground.visits.filter(
            user=request.user, visit_type=Visit.VisitType.VISITED
        ).exists()
    )
    visit_count = (
        ground.visits.filter(visit_type=Visit.VisitType.VISITED)
        .values("user")
        .distinct()
        .count()
    )
    return render(
        request,
        "grounds/ground_detail.html",
        {
            "ground": ground,
            "user_has_visited": user_has_visited,
            "visit_count": visit_count,
        },
    )


@login_required
def claim_ground(request, slug):
    if request.method != "POST":
        return redirect("grounds:detail", slug=slug)
    ground = get_object_or_404(Ground, slug=slug)
    Visit.objects.create(
        user=request.user,
        ground=ground,
        visit_type=Visit.VisitType.VISITED,
        visited_on=date.today(),
    )
    return redirect("grounds:detail", slug=slug)
