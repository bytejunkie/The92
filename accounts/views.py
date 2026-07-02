import io

from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count, Max, OuterRef, Q, Subquery
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from PIL import Image, ImageDraw, ImageFont

from grounds.models import Ground, Visit

from .forms import EditProfileForm, RegisterForm
from .models import Follow
from .share import build_share_message

User = get_user_model()

VALID_TABS = {"visited", "want-to-go"}

_VISITED_TYPES = [Visit.VisitType.VISITED, Visit.VisitType.HISTORIC]
TOTAL_GROUNDS = 92


def _visited_count(profile_user):
    return (
        Visit.objects.filter(user=profile_user, visit_type__in=_VISITED_TYPES)
        .values("ground")
        .distinct()
        .count()
    )


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
            visit_type__in=_VISITED_TYPES,
        )
        .order_by("-pk")
        .values("pk")[:1]
    )
    visited_grounds = (
        Ground.objects.filter(
            visits__user=profile_user,
            visits__visit_type__in=_VISITED_TYPES,
        )
        .select_related("team")
        .annotate(
            last_visit=Max(
                "visits__visited_on",
                filter=Q(visits__user=profile_user, visits__visit_type__in=_VISITED_TYPES),
            ),
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

    follower_count = Follow.objects.filter(following=profile_user).count()
    following_count = Follow.objects.filter(follower=profile_user).count()

    share_url = request.build_absolute_uri(reverse("grounds:home"))
    share_card_url = request.build_absolute_uri(
        reverse("accounts:share_card_image", args=[profile_user.username])
    )
    share_text = build_share_message(visited_count, TOTAL_GROUNDS)
    share_label = "Share your 92" if is_own_profile else f"Share {profile_user.username}'s 92"

    return render(
        request,
        "accounts/profile.html",
        {
            "profile_user": profile_user,
            "visited_grounds": visited_grounds,
            "visited_count": visited_count,
            "want_to_go": want_to_go,
            "total_count": TOTAL_GROUNDS,
            "is_own_profile": is_own_profile,
            "viewer_follows": viewer_follows,
            "can_see_wishlist": can_see_wishlist,
            "follower_count": follower_count,
            "following_count": following_count,
            "current_tab": tab,
            "share_url": share_url,
            "share_card_url": share_card_url,
            "share_text": share_text,
            "share_label": share_label,
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


def visitor_ranking():
    """Users annotated with `visited` (distinct grounds visited), ranked.
    Tie-break: whoever joined earlier ranks higher. Shared by the leaderboard
    page and the home-page top-5 preview."""
    return (
        User.objects.annotate(
            visited=Count(
                "visits__ground",
                filter=Q(visits__visit_type__in=_VISITED_TYPES),
                distinct=True,
            )
        )
        .filter(visited__gt=0)
        .order_by("-visited", "date_joined")
    )


def leaderboard(request):
    """Rank ground-hoppers by distinct grounds visited. Global, or scoped to
    the people the viewer follows (plus themselves)."""
    scope = request.GET.get("scope", "global")
    if scope == "friends" and not request.user.is_authenticated:
        scope = "global"

    ranking = visitor_ranking()

    if scope == "friends":
        friend_ids = list(
            Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
        )
        ranking = ranking.filter(pk__in=friend_ids + [request.user.pk])

    my_rank = None
    my_visited = 0
    if request.user.is_authenticated:
        me = ranking.filter(pk=request.user.pk).first()
        if me:
            my_visited = me.visited
            my_rank = (
                ranking.filter(
                    Q(visited__gt=me.visited)
                    | Q(visited=me.visited, date_joined__lt=request.user.date_joined)
                ).count()
                + 1
            )

    paginator = Paginator(ranking, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "accounts/leaderboard.html",
        {
            "page_obj": page_obj,
            "scope": scope,
            "start_rank": (page_obj.number - 1) * paginator.per_page,
            "total_count": TOTAL_GROUNDS,
            "my_rank": my_rank,
            "my_visited": my_visited,
            "player_count": paginator.count,
        },
    )


def share_profile(request, username):
    profile_user = get_object_or_404(User, username=username)
    visited_count = _visited_count(profile_user)
    share_url = request.build_absolute_uri(reverse("grounds:home"))
    share_card_url = request.build_absolute_uri(
        reverse("accounts:share_card_image", args=[profile_user.username])
    )
    share_text = build_share_message(visited_count, TOTAL_GROUNDS)

    # Forum-signature banner + ready-to-paste embed codes (link back = traffic)
    sig_url = request.build_absolute_uri(
        reverse("accounts:signature_image", args=[profile_user.username])
    )
    sig_url_dark = sig_url + "?theme=dark"
    profile_link = request.build_absolute_uri(
        reverse("accounts:profile_user", args=[profile_user.username])
    )

    def _embed(img_url):
        alt = f"The 92 — {profile_user.username}"
        return {
            "bbcode": f"[url={profile_link}][img]{img_url}[/img][/url]",
            "html": f'<a href="{profile_link}"><img src="{img_url}" alt="{alt}"></a>',
            "markdown": f"[![{alt}]({img_url})]({profile_link})",
        }

    return render(
        request,
        "accounts/share.html",
        {
            "profile_user": profile_user,
            "visited_count": visited_count,
            "total_count": TOTAL_GROUNDS,
            "share_url": share_url,
            "share_card_url": share_card_url,
            "share_text": share_text,
            "sig_url": sig_url,
            "sig_url_dark": sig_url_dark,
            "forum_light": _embed(sig_url),
            "forum_dark": _embed(sig_url_dark),
        },
    )


def share_card_image(request, username):
    profile_user = get_object_or_404(User, username=username)
    visited_count = _visited_count(profile_user)
    accent = "#19704B"
    if profile_user.favourite_team_id:
        accent = profile_user.favourite_team.primary_colour

    width, height = 1200, 630
    img = Image.new("RGB", (width, height), "#0b3d28")
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, 12], fill=accent)

    eyebrow_font = ImageFont.load_default(size=32)
    title_font = ImageFont.load_default(size=72)
    stat_font = ImageFont.load_default(size=120)
    label_font = ImageFont.load_default(size=36)

    draw.text((64, 64), "THE 92", font=eyebrow_font, fill="#9fd8b8")
    draw.text((64, 120), profile_user.username, font=title_font, fill="#ffffff")

    stat_text = f"{visited_count} / {TOTAL_GROUNDS}"
    draw.text((64, 280), stat_text, font=stat_font, fill="#ffffff")
    draw.text((64, 420), "grounds visited", font=label_font, fill="#9fd8b8")

    bar_x, bar_y, bar_w, bar_h = 64, 500, width - 128, 28
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h // 2, fill="#0f4d33"
    )
    progress_w = int(bar_w * min(visited_count / TOTAL_GROUNDS, 1.0))
    if progress_w > bar_h:
        draw.rounded_rectangle(
            [bar_x, bar_y, bar_x + progress_w, bar_y + bar_h], radius=bar_h // 2, fill=accent
        )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    response = HttpResponse(buf.getvalue(), content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    return response


# Forum-signature banner palettes (light / dark), keyed to the design tokens.
_SIG_LIGHT = {
    "bg": "#ffffff", "border": "#dee4de", "ink": "#101820", "muted": "#5d6975",
    "dot_off": "#e3e8e3", "dot_on": "#19704b", "pitch": "#19704b",
    "ball": "#101820", "lime": "#bdeb80",
}
_SIG_DARK = {
    "bg": "#12191f", "border": "#26313a", "ink": "#f4f8f4", "muted": "#9aa8ae",
    "dot_off": "#26313a", "dot_on": "#34c07e", "pitch": "#34c07e",
    "ball": "#f4f8f4", "lime": "#bdeb80",
}


def signature_image(request, username):
    """Wide 'forum signature' banner: gold avatar, name/@handle, team, the
    92-dot collection grid and the site URL. Self-updating as visits grow.
    Add ?theme=dark for the dark variant. Mirrors the Figma profile module."""
    profile_user = get_object_or_404(User, username=username)
    visited = _visited_count(profile_user)
    c = _SIG_DARK if request.GET.get("theme") == "dark" else _SIG_LIGHT

    display_name = profile_user.get_full_name() or profile_user.username
    parts = display_name.split()
    if len(parts) >= 2:
        initials = (parts[0][:1] + parts[1][:1]).upper()
    else:
        initials = profile_user.username[:2].upper()

    team = profile_user.favourite_team if profile_user.favourite_team_id else None
    team_colour = team.primary_colour if team else "#427bd3"

    W, H = 740, 190
    img = Image.new("RGB", (W, H), c["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, H - 1], outline=c["border"], width=1)
    d.rectangle([0, 0, 6, H], fill=team_colour)  # team accent stripe

    f_name = ImageFont.load_default(size=30)
    f_handle = ImageFont.load_default(size=18)
    f_word = ImageFont.load_default(size=22)
    f_stat = ImageFont.load_default(size=42)
    f_small = ImageFont.load_default(size=16)
    f_init = ImageFont.load_default(size=22)

    # Gold avatar with initials
    d.ellipse([28, 24, 84, 80], fill="#eeb34c")
    d.text((56, 52), initials, font=f_init, fill="#101820", anchor="mm")

    # Name + handle (+ team)
    d.text((100, 24), display_name, font=f_name, fill=c["ink"])
    handle = f"@{profile_user.username}"
    if team:
        handle += f"  ·  {team.name}"
    d.ellipse([100, 68, 108, 76], fill=team_colour)
    d.text((116, 61), handle, font=f_handle, fill=c["muted"])

    # 92-dot collection grid (23 x 4)
    gx, gy, step, r = 100, 106, 11, 3.5
    for i in range(TOTAL_GROUNDS):
        col, row = i % 23, i // 23
        cx, cy = gx + col * step, gy + row * step
        fill = c["dot_on"] if i < visited else c["dot_off"]
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    d.text((100, 158), f"{visited} of {TOTAL_GROUNDS} grounds visited", font=f_small, fill=c["muted"])

    # Divider + right-hand brand block
    d.line([474, 32, 474, 158], fill=c["border"], width=1)
    d.ellipse([500, 34, 528, 62], fill=c["ball"])
    d.ellipse([510, 44, 518, 52], fill=c["lime"])
    d.text((538, 38), "THE 92", font=f_word, fill=c["ink"])
    d.text((500, 82), f"{visited}/{TOTAL_GROUNDS}", font=f_stat, fill=c["pitch"])
    d.text((500, 150), "the92.co.uk", font=f_small, fill=c["ink"])

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    response = HttpResponse(buf.getvalue(), content_type="image/png")
    response["Cache-Control"] = "public, max-age=300"
    return response
