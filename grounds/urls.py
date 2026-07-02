from django.urls import path

from . import views

app_name = "grounds"

urlpatterns = [
    path("", views.home, name="home"),
    path("grounds/", views.ground_list, name="list"),
    path("grounds/<slug:slug>/", views.ground_detail, name="detail"),
    path("grounds/<slug:slug>/claim/", views.claim_ground, name="claim"),
    path("grounds/<slug:slug>/want/", views.want_ground, name="want"),
    path("visits/<int:pk>/delete/", views.delete_visit, name="delete_visit"),
    path("map/", views.ground_map, name="map"),
    path("grounds/<slug:slug>/checkin/", views.checkin_ground, name="checkin"),
    path("grounds/<slug:slug>/historic/", views.add_historic_visit, name="historic"),
    path("grounds/<slug:slug>/suggest/", views.suggest_ground, name="suggest"),
    path("grounds/<slug:slug>/tip/", views.add_tip, name="add_tip"),
]
