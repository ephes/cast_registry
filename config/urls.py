from django.contrib import admin
from django.urls import include, path

from apps.registry.views import (
    create_domain,
    deploy_progress,
    fade_out,
    home,
    list_domains,
    register,
    show_messages,
    deploy_state,
)

urlpatterns = [
    path("", home),
    path("admin/", admin.site.urls),
    path("domain/create/", create_domain, name="create_domain"),
    path("domain/", list_domains, name="list_domains"),
    path("messages/", show_messages, name="messages"),
    path("register/", register, name="register"),
    path("fade_out/", fade_out, name="fade_out"),
    path("deploy-progress/<int:domain_id>/<int:deployment_id>", deploy_progress, name="deploy_progress"),
    path("deploy-state/<int:domain_id>/<int:deployment_id>/", deploy_state, name="deploy_state"),
    # debug toolbar
    path("__debug__/", include("debug_toolbar.urls")),
    # allauth
    path("accounts/", include("allauth.urls")),
]
