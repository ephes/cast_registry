from django.contrib import admin
from django.urls import include, path

from apps.registry.views import (
    create_domain,
    csrf_demo,
    csrf_demo_checker,
    home,
    list_domains,
    messages,
    partial_rendering,
)

urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("demo/", csrf_demo),
    path("demo/checker/", csrf_demo_checker),
    path("partial-rendering/", partial_rendering),
    path("__debug__/", include("debug_toolbar.urls")),
    path("domain/create/", create_domain, name="create_domain"),
    path("domain/", list_domains, name="list_domains"),
    path("messages/", messages, name="messages"),
]
