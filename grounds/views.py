from django.shortcuts import get_object_or_404, render

from .models import Ground


def home(request):
    grounds = Ground.objects.select_related("team")[:3]
    context = {
        "grounds": grounds,
        "visited_count": 57,
        "total_count": 92,
        "friends_count": 248,
    }
    return render(request, "grounds/home.html", context)


def ground_list(request):
    grounds = Ground.objects.select_related("team")
    return render(request, "grounds/ground_list.html", {"grounds": grounds})


def ground_detail(request, slug):
    ground = get_object_or_404(Ground.objects.select_related("team"), slug=slug)
    return render(request, "grounds/ground_detail.html", {"ground": ground})
