from django.contrib import admin
from django.urls import include, path

from apps.registry.views import (
    create_domain,
    csrf_demo,
    csrf_demo_checker,
    fade_out,
    home,
    list_domains,
    messages,
    partial_rendering,
    register,
)

urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("demo/", csrf_demo),
    path("demo/checker/", csrf_demo_checker),
    path("partial-rendering/", partial_rendering),
    path("domain/create/", create_domain, name="create_domain"),
    path("domain/", list_domains, name="list_domains"),
    path("messages/", messages, name="messages"),
    path("register/", register, name="register"),
    path("fade_out/", fade_out, name="fade_out"),
    # debug toolbar
    path("__debug__/", include("debug_toolbar.urls")),
    # allauth
    path("accounts/", include("allauth.urls")),
]
