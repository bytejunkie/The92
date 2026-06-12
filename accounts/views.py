from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db.models import Max, OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render

from grounds.models import Ground, Visit

from .forms import RegisterForm

User = get_user_model()

VALID_TABS = {"visited", "want-to-go", "historic"}


def register(request):
    if request.user.is_authenticated:
        return redirect("grounds:home")
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return redirect("grounds:home")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


def profile(request, username=None):
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        if not request.user.is_authenticated:
            return redirect("login")
        profile_user = request.user

    tab = request.GET.get("tab", "visited")
    if tab not in VALID_TABS:
        tab = "visited"

    latest_visit_pk_sq = (
        Visit.objects.filter(
            user=profile_user,
            ground=OuterRef("pk"),
            visit_type=Visit.VisitType.VISITED,
        )
        .order_by("-pk")
        .values("pk")[:1]
    )
    visited_grounds = (
        Ground.objects.filter(
            visits__user=profile_user,
            visits__visit_type=Visit.VisitType.VISITED,
        )
        .select_related("team")
        .annotate(
            last_visit=Max("visits__visited_on"),
            latest_visit_pk=Subquery(latest_visit_pk_sq),
        )
        .order_by("-last_visit")
        .distinct()
    )
    visited_count = visited_grounds.count()

    want_to_go = (
        Visit.objects.filter(
            user=profile_user, visit_type=Visit.VisitType.WANT_TO_GO
        )
        .select_related("ground__team")
        .order_by("-created_at")
    )

    historic = (
        Visit.objects.filter(
            user=profile_user, visit_type=Visit.VisitType.HISTORIC
        )
        .select_related("ground__team")
        .order_by("-visited_on", "-created_at")
    )

    is_own_profile = request.user.is_authenticated and profile_user == request.user

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "visited_grounds": visited_grounds,
            "visited_count": visited_count,
            "want_to_go": want_to_go,
            "historic": historic,
            "total_count": 92,
            "is_own_profile": is_own_profile,
            "current_tab": tab,
        },
    )
