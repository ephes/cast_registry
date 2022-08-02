from unittest.mock import patch

import pytest
from django.urls import reverse

from ..fastdeploy import SpecialSteps
from ..models import Domain
from ..views import render_partial_or_full


def test_get_home(client):
    r = client.get(reverse("home"))
    assert r.status_code == 200


def test_get_fade_out(client):
    r = client.get(reverse("fade_out"))
    assert r.status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method, url",
    [
        ("get", reverse("domains")),
        ("post", reverse("domains")),
        ("get", reverse("domain_deployments", kwargs={"domain_id": 1})),
        ("post", reverse("domain_deployments", kwargs={"domain_id": 1})),
        ("get", reverse("deploy_state", kwargs={"deployment_id": 1})),
    ],
)
def test_get_login_required_not_authenticated(client, method, url):
    r = client.get(url)
    assert r.status_code == 302
    assert "login" in r.url


@pytest.mark.django_db
def test_get_domains_authenticated(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("domains")
    r = client.get(url)
    assert r.status_code == 200
    assert "form hx-post" in r.content.decode("utf8")


@pytest.mark.django_db
def test_get_domain_deployments_authenticated(client, domain):
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse("domain_deployments", kwargs={"domain_id": domain.pk})
    r = client.get(url)
    assert r.status_code == 200
    assert "form hx-post" in r.content.decode("utf8")


@pytest.mark.django_db
def test_post_domain_deployments_authorized(client, domain):
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse("domain_deployments", kwargs={"domain_id": domain.pk})
    r = client.post(url, data={"target": "DP"})
    assert r.status_code == 302
    assert r.url == url


def test_post_domain_deployments_invalid_form(client, domain):
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse("domain_deployments", kwargs={"domain_id": domain.pk})
    r = client.post(url, data={"target": "ASDF"})
    assert r.status_code == 200
    html = r.content.decode("utf8")
    assert "errorlist" in html


def test_post_domains_authenticated(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("domains")
    r = client.post(url, data={"fqdn": "my.domain.staging.django-cast.com", "backend": Domain.Backend.CAST})
    assert r.status_code == 302
    assert r.url == url


def test_post_domains_authenticated_invalid_form(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("domains")
    r = client.post(url, data={"foo": "my.domain.staging.django-cast.com"})
    assert r.status_code == 200
    assert "This field is required." in r.content.decode("utf8")


def test_get_login_required_deploy_state_authenticated(client, deployment):
    domain = deployment.domain
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse("deploy_state", kwargs={"deployment_id": deployment.pk})
    steps = [SpecialSteps.START.value]
    with patch("apps.registry.models.Deployment.get_new_steps", return_value=steps):
        r = client.get(url)
    assert r.status_code == 200
    assert "aside" in r.content.decode("utf8")


@pytest.fixture
def other_user(django_user_model):
    username, password = "user2", "password"
    user = django_user_model.objects.create_user(username=username, password=password)
    user._password = password
    return user


@pytest.mark.django_db
def test_get_domain_deployments_not_authorized(client, domain, other_user):
    client.login(username=other_user.username, password=other_user._password)
    url = reverse("domain_deployments", kwargs={"domain_id": domain.pk})
    r = client.get(url)
    assert r.status_code == 403


@pytest.mark.django_db
def test_get_deploy_state_not_authorized(client, deployment, other_user):
    client.login(username=other_user.username, password=other_user._password)
    url = reverse("deploy_state", kwargs={"deployment_id": deployment.pk})
    r = client.get(url)
    assert r.status_code == 403


@pytest.mark.django_db
def test_get_deployment_state_finished_has_stop_polling_status(client, user, finished_deployment, remote_deployment):
    """
    Use user fixture because user._password gets lost by fetching user from db.
    """
    client.login(username=user.username, password=user._password)
    url = reverse("deploy_state", kwargs={"deployment_id": finished_deployment.pk})
    steps = [SpecialSteps.END.value]
    with patch("apps.registry.models.Deployment.get_new_steps", return_value=steps):
        r = client.get(url)
    assert r.status_code == 286


class Request:
    META = {"CSRF_COOKIE": "asdf"}

    def __init__(self, is_htmx):
        self.htmx = is_htmx


def test_render_full_when_htmx_is_false():
    r = render_partial_or_full(Request(False), "domains.html", {})
    html = r.content.decode("utf8")
    assert "doctype html" in html


def test_render_partial_when_htmx_is_true():
    r = render_partial_or_full(Request(True), "domains.html", {})
    html = r.content.decode("utf8")
    assert "doctype html" not in html
