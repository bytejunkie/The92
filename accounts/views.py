from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render

from grounds.models import Ground, Visit

from .forms import RegisterForm

User = get_user_model()


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

    visited_grounds = (
        Ground.objects.filter(
            visits__user=profile_user,
            visits__visit_type=Visit.VisitType.VISITED,
        )
        .select_related("team")
        .annotate(last_visit=Max("visits__visited_on"))
        .order_by("-last_visit")
        .distinct()
    )
    visited_count = visited_grounds.count()

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "visited_grounds": visited_grounds,
            "visited_count": visited_count,
            "total_count": 92,
            "is_own_profile": request.user.is_authenticated and profile_user == request.user,
        },
    )
