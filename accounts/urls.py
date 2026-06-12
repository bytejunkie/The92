from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile, name="profile_user"),
    path("profile/<str:username>/follow/", views.follow_user, name="follow"),
    path("feed/", views.feed, name="feed"),
]
