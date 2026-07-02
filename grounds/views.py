from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from accounts.models import Follow
from accounts.share import build_share_message

from .models import Ground, GroundSuggestion, GroundTip, Match, Team, Visit

TOTAL_GROUNDS = 92

User = get_user_model()

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
    share_url = ""
    share_card_url = ""
    share_text = ""
    if request.user.is_authenticated:
        visited_count = (
            Visit.objects.filter(
                user=request.user,
                visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC],
            )
            .values("ground")
            .distinct()
            .count()
        )
        share_url = request.build_absolute_uri(reverse("grounds:home"))
        share_card_url = request.build_absolute_uri(
            reverse("accounts:share_card_image", args=[request.user.username])
        )
        share_text = build_share_message(visited_count, TOTAL_GROUNDS)
    friends_count = 0
    if request.user.is_authenticated:
        friends_count = Follow.objects.filter(follower=request.user).count()
    from accounts.views import visitor_ranking

    top_visitors = list(visitor_ranking()[:5])
    context = {
        "grounds": grounds,
        "visited_count": visited_count,
        "total_count": 92,
        "friends_count": friends_count,
        "top_visitors": top_visitors,
        "share_url": share_url,
        "share_card_url": share_card_url,
        "share_text": share_text,
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
                user=request.user,
                visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC],
            ).values_list("ground_id", flat=True).distinct()
        )

    today_ground_ids = set(
        Match.objects.filter(
            kickoff__date=date.today(),
            status__in=["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED"],
        ).values_list("ground_id", flat=True)
    )

    paginator = Paginator(grounds, 24)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "grounds": page_obj,
        "page_obj": page_obj,
        "ground_count": paginator.count,
        "current_league": league,
        "current_q": q,
        "visited_ground_ids": visited_ground_ids,
        "today_ground_ids": today_ground_ids,
    }
    return render(request, "grounds/ground_list.html", context)


def ground_detail(request, slug):
    ground = get_object_or_404(Ground.objects.select_related("team"), slug=slug)
    user_has_visited = False
    user_wants_to_go = False
    user_latest_visit = None
    if request.user.is_authenticated:
        user_visits = ground.visits.filter(user=request.user)
        user_has_visited = user_visits.filter(
            visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC]
        ).exists()
        user_wants_to_go = user_visits.filter(visit_type=Visit.VisitType.WANT_TO_GO).exists()
        user_latest_visit = (
            user_visits
            .filter(visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC])
            .select_related("match__away_team")
            .order_by("-visited_on", "-created_at")
            .first()
        )
    visit_count = (
        ground.visits.filter(
            visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC]
        )
        .values("user")
        .distinct()
        .count()
    )
    friends_here = []
    if request.user.is_authenticated:
        following_ids = Follow.objects.filter(
            follower=request.user
        ).values_list("following_id", flat=True)
        friends_here = list(
            User.objects.filter(
                visits__ground=ground,
                visits__visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC],
                pk__in=following_ids,
            ).distinct()[:8]
        )
    guide_stale = (
        ground.info_updated_at is not None
        and ground.info_updated_at < date.today() - timedelta(days=365)
    )

    # Next fixture: today first, then soonest upcoming
    next_match = (
        ground.matches
        .filter(status__in=["SCHEDULED", "TIMED", "IN_PLAY", "PAUSED"])
        .select_related("home_team", "away_team")
        .order_by("kickoff")
        .first()
    )
    today_match = next_match if (next_match and next_match.kickoff.date() == date.today()) else None
    approved_tips = list(
        ground.tips.filter(is_approved=True).select_related("user").order_by("category", "-created_at")
    )
    user_pending_suggestions = []
    show_share_prompt = False
    user_total_visited = 0
    share_url = ""
    share_card_url = ""
    share_text = ""
    if request.user.is_authenticated:
        user_pending_suggestions = list(
            ground.suggestions.filter(user=request.user, status=GroundSuggestion.Status.PENDING)
            .values_list("field_name", flat=True)
        )
        if request.GET.get("claimed"):
            show_share_prompt = True
            user_total_visited = (
                Visit.objects.filter(
                    user=request.user,
                    visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC],
                )
                .values("ground")
                .distinct()
                .count()
            )
            share_url = request.build_absolute_uri(reverse("grounds:home"))
            share_card_url = request.build_absolute_uri(
                reverse("accounts:share_card_image", args=[request.user.username])
            )
            share_text = build_share_message(user_total_visited, TOTAL_GROUNDS, ground_name=ground.name)
    return render(
        request,
        "grounds/ground_detail.html",
        {
            "ground": ground,
            "user_has_visited": user_has_visited,
            "user_latest_visit": user_latest_visit,
            "user_wants_to_go": user_wants_to_go,
            "visit_count": visit_count,
            "friends_here": friends_here,
            "guide_stale": guide_stale,
            "approved_tips": approved_tips,
            "user_pending_suggestions": user_pending_suggestions,
            "next_match": next_match,
            "today_match": today_match,
            "show_share_prompt": show_share_prompt,
            "user_total_visited": user_total_visited,
            "share_url": share_url,
            "share_card_url": share_card_url,
            "share_text": share_text,
        },
    )


@login_required
def checkin_ground(request, slug):
    """Matchday check-in — links visit to today's match."""
    if request.method != "POST":
        return redirect("grounds:detail", slug=slug)
    ground = get_object_or_404(Ground, slug=slug)
    match_id = request.POST.get("match_id")
    match = None
    if match_id:
        match = Match.objects.filter(pk=match_id, ground=ground).first()
    Visit.objects.create(
        user=request.user,
        ground=ground,
        visit_type=Visit.VisitType.VISITED,
        visited_on=date.today(),
        match=match,
    )
    return redirect(f"{ground.get_absolute_url()}?claimed=1")


@login_required
def add_historic_visit(request, slug):
    import json as _json
    ground = get_object_or_404(Ground.objects.select_related("team"), slug=slug)

    if request.method == "POST":
        match_id = request.POST.get("match_id", "").strip()
        if not match_id:
            return redirect("grounds:historic", slug=slug)
        match = Match.objects.filter(pk=match_id, ground=ground).select_related("away_team").first()
        if not match:
            return redirect("grounds:historic", slug=slug)
        Visit.objects.get_or_create(
            user=request.user,
            ground=ground,
            match=match,
            defaults={
                "visit_type": Visit.VisitType.HISTORIC,
                "visited_on": match.kickoff.date(),
            },
        )
        return redirect(f"{ground.get_absolute_url()}?claimed=1")

    # GET — build opponent list and match JSON for JS filtering
    all_matches = list(
        ground.matches
        .select_related("away_team")
        .order_by("-kickoff")
    )

    def _match_label(m):
        away = m.away_team.name if m.away_team else "Unknown"
        d = m.kickoff.strftime("%d %b %Y")
        score = (
            f"{m.home_score}–{m.away_score}"
            if m.home_score is not None and m.away_score is not None
            else None
        )
        return f"vs {away} · {d}" + (f" · {score}" if score else "")

    # {away_team_id: [{id, label}, ...]}
    matches_by_opponent: dict = {}
    for m in all_matches:
        if not m.away_team_id:
            continue
        matches_by_opponent.setdefault(m.away_team_id, []).append({
            "id": m.pk,
            "label": _match_label(m),
        })

    opponent_ids = list(matches_by_opponent.keys())
    opponents = list(Team.objects.filter(pk__in=opponent_ids).order_by("name"))

    fave = getattr(request.user, "favourite_team", None)
    if fave and fave.pk in matches_by_opponent:
        opponents = [fave] + [t for t in opponents if t.pk != fave.pk]

    return render(request, "grounds/historic_visit.html", {
        "ground": ground,
        "opponents": opponents,
        "matches_data": matches_by_opponent,
        "fave_team_id": fave.pk if fave else None,
    })


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
    return redirect(f"{ground.get_absolute_url()}?claimed=1")


@login_required
def want_ground(request, slug):
    if request.method != "POST":
        return redirect("grounds:detail", slug=slug)
    ground = get_object_or_404(Ground, slug=slug)
    existing = Visit.objects.filter(
        user=request.user, ground=ground, visit_type=Visit.VisitType.WANT_TO_GO
    ).first()
    if existing:
        existing.delete()
    else:
        Visit.objects.create(
            user=request.user,
            ground=ground,
            visit_type=Visit.VisitType.WANT_TO_GO,
        )
    return redirect("grounds:detail", slug=slug)


@login_required
def delete_visit(request, pk):
    visit = get_object_or_404(Visit, pk=pk, user=request.user)
    if request.method == "POST":
        visit.delete()
        return redirect("accounts:profile")
    return render(request, "grounds/visit_confirm_delete.html", {"visit": visit})


def ground_map(request):
    grounds_qs = (
        Ground.objects.select_related("team")
        .filter(latitude__isnull=False, longitude__isnull=False)
        .annotate(league_order=LEAGUE_ORDER)
        .order_by("league_order", "team__name")
    )

    visited_ids: set[int] = set()
    want_ids: set[int] = set()
    if request.user.is_authenticated:
        visited_ids = set(
            Visit.objects.filter(
                user=request.user,
                visit_type__in=[Visit.VisitType.VISITED, Visit.VisitType.HISTORIC],
            ).values_list("ground_id", flat=True).distinct()
        )
        want_ids = set(
            Visit.objects.filter(
                user=request.user, visit_type=Visit.VisitType.WANT_TO_GO
            ).values_list("ground_id", flat=True).distinct()
        )

    grounds_data = []
    for g in grounds_qs:
        if g.pk in visited_ids:
            status = "visited"
        elif g.pk in want_ids:
            status = "want"
        else:
            status = "unvisited"
        grounds_data.append({
            "name": g.name,
            "team": g.team.name if g.team else "",
            "league": g.team.get_league_level_display() if g.team else "",
            "capacity": g.capacity,
            "lat": float(g.latitude),
            "lng": float(g.longitude),
            "url": g.get_absolute_url(),
            "status": status,
            "colour": g.team.primary_colour if g.team else "#19704B",
        })

    visited_count = len(visited_ids)
    want_count = len(want_ids)

    return render(request, "grounds/map.html", {
        "grounds_json": grounds_data,
        "visited_count": visited_count,
        "want_count": want_count,
        "total_count": len(grounds_data),
    })


@login_required
def suggest_ground(request, slug):
    ground = get_object_or_404(Ground.objects.select_related("team"), slug=slug)
    if request.method != "POST":
        return redirect("grounds:detail", slug=slug)

    field_name = request.POST.get("field_name", "").strip()
    valid_fields = {c[0] for c in GroundSuggestion.FieldName.choices}
    if not field_name or field_name not in valid_fields:
        return redirect("grounds:detail", slug=slug)

    if field_name in GroundSuggestion.IMAGE_FIELDS:
        proposed_image = request.FILES.get("proposed_image")
        if not proposed_image:
            return redirect("grounds:detail", slug=slug)
        GroundSuggestion.objects.create(
            ground=ground,
            user=request.user,
            field_name=field_name,
            proposed_image=proposed_image,
        )
    else:
        proposed_value = request.POST.get("proposed_value", "").strip()
        if not proposed_value:
            return redirect("grounds:detail", slug=slug)
        GroundSuggestion.objects.create(
            ground=ground,
            user=request.user,
            field_name=field_name,
            proposed_value=proposed_value[:500],
        )
    return redirect("grounds:detail", slug=slug)


@login_required
def add_tip(request, slug):
    ground = get_object_or_404(Ground, slug=slug)
    if request.method != "POST":
        return redirect("grounds:detail", slug=slug)

    category = request.POST.get("category", "").strip()
    body = request.POST.get("body", "").strip()

    valid_cats = {c[0] for c in GroundTip.Category.choices}
    if not category or category not in valid_cats or not body:
        return redirect("grounds:detail", slug=slug)

    GroundTip.objects.create(
        ground=ground,
        user=request.user,
        category=category,
        body=body[:280],
    )
    return redirect("grounds:detail", slug=slug)
