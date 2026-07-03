"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from django.views.static import serve as media_serve

from accounts.views import RateLimitedLoginView

urlpatterns = [
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path("", include("grounds.urls")),
    path("accounts/", include("accounts.urls")),
    path("accounts/login/", RateLimitedLoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/", include("allauth.urls")),
    path("admin/", admin.site.urls),
]

# Serve user-uploaded media (ground photos, suggestions) from MEDIA_ROOT — on
# Railway that's the persistent volume. WhiteNoise only handles static assets,
# and Django's static() helper is a no-op when DEBUG is False, so serve it
# directly. Fine at our scale; move to object storage (R2/S3) if media grows.
urlpatterns += [
    re_path(
        r"^media/(?P<path>.*)$",
        media_serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]
