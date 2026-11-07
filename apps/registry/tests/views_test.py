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


@pytest.mark.django_db
def test_post_domain_deployments_start_deployment_exception(client, domain):
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse("domain_deployments", kwargs={"domain_id": domain.pk})
    with patch("apps.registry.models.Deployment.start", side_effect=Exception("Test")):
        r = client.post(url, data={"target": "DP"}, follow=True)
    success_msg, error_msg = r.context["messages"]
    assert str(success_msg) == "Deployment created successfully"
    assert str(error_msg) == "Could not start deployment due to: Test"


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


@pytest.mark.django_db
@pytest.mark.parametrize("finished", [False, True])
@pytest.mark.parametrize(
    "name, escaped",
    [
        ("Compile files", "Compile files"),
        ('<img src=x onerror="alert(1)">', "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"),
        ("<script>alert('x')</script> & done", "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt; &amp; done"),
    ],
)
def test_deploy_state_escapes_remote_step_text(client, deployment, finished, name, escaped):
    from django.utils import timezone

    from ..fastdeploy import RemoteDeployment, Step

    client.force_login(deployment.domain.owner)
    deployment.data = RemoteDeployment(id=1, no_steps_yet=True)
    deployment.save()
    remote = RemoteDeployment(id=1, steps=[Step(id=1, name=name)], finished=timezone.now() if finished else None)
    with patch("apps.registry.fastdeploy.TestClient.fetch_deployment", return_value=remote):
        response = client.get(reverse("deploy_state", args=[deployment.pk]))
    assert response.status_code == (286 if finished else 200)
    assert f"<aside>{escaped}</aside>" in response.content.decode()
    assert b"<script>" not in response.content
    assert b"<img" not in response.content


@pytest.mark.django_db
@pytest.mark.parametrize(
    "query, expected_page",
    [("", 1), ("?page=2", 2), ("?page=3", 3), ("?page=invalid", 1), ("?page=99", 3), ("?page=1&page=2", 2)],
)
@pytest.mark.parametrize("listing", ["domains", "deployments"])
def test_owner_list_pagination(client, user, other_user, query, expected_page, listing):
    from ..models import Deployment

    owned = [Domain.objects.create(owner=user, fqdn=f"domain-{i}.example.com") for i in range(5)]
    foreign = Domain.objects.create(owner=other_user, fqdn="foreign.example.com")
    if listing == "domains":
        url = reverse("domains")
        expected = owned
    else:
        url = reverse("domain_deployments", args=[owned[0].pk])
        expected = [Deployment.objects.create(domain=owned[0]) for _ in range(5)]
        Deployment.objects.create(domain=foreign)
        Deployment.objects.create(domain=owned[1])
    client.force_login(user)
    response = client.get(url + query)
    assert response.status_code == 200
    page = response.context["page"]
    assert page.number == expected_page
    assert page.paginator.count == 5
    start = (expected_page - 1) * 2
    stop = start + 2
    assert list(page.object_list) == expected[start:stop]
    if listing == "domains":
        assert b"foreign.example.com" not in response.content
