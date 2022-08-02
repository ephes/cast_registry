from typing import Any

from django.urls import path  # noqa

from . import views  # noqa

app_name = "registry"

urlpatterns: list[Any] = [
    path("", views.home),
    path("domains/", views.domains, name="domains"),
    path("domain-deployments/<int:domain_id>/", views.domain_deployments, name="domain_deployments"),
    path("fade_out/", views.fade_out, name="fade_out"),
    path("deploy-state/<int:deployment_id>/", views.deploy_state, name="deploy_state"),
]
