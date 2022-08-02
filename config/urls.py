from typing import Any

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.registry.urls import urlpatterns as registry_urlpatterns

urlpatterns: list[Any] = [
    # admin
    path(settings.ADMIN_URL, admin.site.urls),
    # debug toolbar
    path("__debug__/", include("debug_toolbar.urls")),
    # allauth
    path("accounts/", include("allauth.urls")),
] + registry_urlpatterns
