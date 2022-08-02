from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from apps.registry.views import (
    deploy_state,
    domain_deployments,
    domains,
    fade_out,
    home,
)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", home),
    path("domains/", domains, name="domains"),
    path("domain-deployments/<int:domain_id>/", domain_deployments, name="domain_deployments"),
    path("fade_out/", fade_out, name="fade_out"),
    path("deploy-state/<int:deployment_id>/", deploy_state, name="deploy_state"),
    # debug toolbar
    path("__debug__/", include("debug_toolbar.urls")),
    # allauth
    path("accounts/", include("allauth.urls")),
]
