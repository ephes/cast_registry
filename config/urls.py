from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.registry.views import (
    deploy_progress,
    deploy_state,
    domain_deployments,
    domains,
    fade_out,
    home,
    register,
)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", home),
    path("domains/", domains, name="domains"),
    path("domain-deployments/<int:domain_id>/", domain_deployments, name="domain_deployments"),
    path("register/", register, name="register"),
    path("fade_out/", fade_out, name="fade_out"),
    path("deploy-progress/<int:domain_id>/<int:deployment_id>", deploy_progress, name="deploy_progress"),
    path("deploy-state/<int:domain_id>/<int:deployment_id>/", deploy_state, name="deploy_state"),
    # debug toolbar
    path("__debug__/", include("debug_toolbar.urls")),
    # allauth
    path("accounts/", include("allauth.urls")),
]
