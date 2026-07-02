from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("profile/<str:username>/", views.profile, name="profile_user"),
    path("profile/<str:username>/follow/", views.follow_user, name="follow"),
    path("profile/<str:username>/share/", views.share_profile, name="share_profile"),
    path("profile/<str:username>/share-card.png", views.share_card_image, name="share_card_image"),
    path("profile/<str:username>/signature.png", views.signature_image, name="signature_image"),
    path("feed/", views.feed, name="feed"),
    path("leaderboard/", views.leaderboard, name="leaderboard"),
]
