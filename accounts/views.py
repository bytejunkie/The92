from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Max, OuterRef, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit

from grounds.models import Ground, Visit

from .forms import EditProfileForm, RegisterForm
from .models import Follow

User = get_user_model()

VALID_TABS = {"visited", "want-to-go", "historic"}


@method_decorator(
    ratelimit(key="ip", rate="10/10m", method="POST", block=True),
    name="dispatch",
)
class RateLimitedLoginView(LoginView):
    pass


@ratelimit(key="ip", rate="10/10m", method="POST", block=True)
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

    is_own_profile = request.user.is_authenticated and profile_user == request.user
    viewer_follows = (
        request.user.is_authenticated
        and not is_own_profile
        and Follow.objects.filter(follower=request.user, following=profile_user).exists()
    )
    can_see_wishlist = is_own_profile or viewer_follows

    tab = request.GET.get("tab", "visited")
    if tab not in VALID_TABS:
        tab = "visited"
    # Hide want-to-go tab from non-followers
    if tab == "want-to-go" and not can_see_wishlist:
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
        Visit.objects.filter(user=profile_user, visit_type=Visit.VisitType.WANT_TO_GO)
        .select_related("ground__team")
        .order_by("-created_at")
    )

    historic = (
        Visit.objects.filter(user=profile_user, visit_type=Visit.VisitType.HISTORIC)
        .select_related("ground__team")
        .order_by("-visited_on", "-created_at")
    )

    follower_count = Follow.objects.filter(following=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()

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
            "viewer_follows": viewer_follows,
            "can_see_wishlist": can_see_wishlist,
            "follower_count": follower_count,
            "following_count": following_count,
            "current_tab": tab,
        },
    )


@login_required
def edit_profile(request):
    if request.method == "POST":
        form = EditProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = EditProfileForm(instance=request.user)
    return render(request, "accounts/edit_profile.html", {"form": form})


@login_required
def follow_user(request, username):
    if request.method != "POST":
        return redirect("accounts:profile_user", username=username)
    target = get_object_or_404(User, username=username)
    if target == request.user:
        return redirect("accounts:profile_user", username=username)
    existing = Follow.objects.filter(follower=request.user, following=target).first()
    if existing:
        existing.delete()
    else:
        Follow.objects.create(follower=request.user, following=target)
    return redirect("accounts:profile_user", username=username)


@login_required
def feed(request):
    following_ids = Follow.objects.filter(
        follower=request.user
    ).values_list("following_id", flat=True)
    visits = (
        Visit.objects.filter(
            user_id__in=following_ids,
            visit_type=Visit.VisitType.VISITED,
        )
        .select_related("user", "ground__team")
        .order_by("-created_at")[:50]
    )
    return render(request, "accounts/feed.html", {"visits": visits, "following_count": len(following_ids)})
