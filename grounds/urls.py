from django.urls import path

from . import views

app_name = "grounds"

urlpatterns = [
    path("", views.home, name="home"),
    path("grounds/", views.ground_list, name="list"),
    path("grounds/<slug:slug>/", views.ground_detail, name="detail"),
    path("grounds/<slug:slug>/claim/", views.claim_ground, name="claim"),
]
