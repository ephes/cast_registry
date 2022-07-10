# from unittest.mock import patch

import pytest
from django.urls import reverse

# from ..fastdeploy import SpecialSteps


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method, url",
    [
        ("get", reverse("domains")),
        ("post", reverse("domains")),
        ("get", reverse("deploy_progress", kwargs={"domain_id": 1, "deployment_id": 1})),
        ("get", reverse("deploy_state", kwargs={"domain_id": 1, "deployment_id": 1})),
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


def test_post_domains_authenticated(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("domains")
    r = client.post(url, data={"fqdn": "my.domain.staging.django-cast.com"})
    assert r.status_code == 302
    assert r.url == reverse("domains")


def test_post_domains_authenticated_invalid_form(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("domains")
    r = client.post(url, data={"foo": "my.domain.staging.django-cast.com"})
    assert r.status_code == 200
    assert "This field is required." in r.content.decode("utf8")


def test_get_login_required_deploy_progress_authenticated(client, domain):
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse("deploy_progress", kwargs={"domain_id": domain.pk, "deployment_id": 1})
    r = client.get(url)
    assert r.status_code == 200
    assert "staging.django-cast.com" in r.content.decode("utf8")


# def test_get_login_required_deploy_state_authenticated(client, domain):
#     user = domain.owner
#     client.login(username=user.username, password=user._password)
#     url = reverse("deploy_state", kwargs={"domain_id": domain.pk, "deployment_id": 1})
#     steps = [SpecialSteps.START.value]
#     with patch("apps.registry.models.Domain.get_new_steps", return_value=(steps, False)):
#         r = client.get(url)
#     assert r.status_code == 200
#     assert "aside" in r.content.decode("utf8")


@pytest.fixture
def other_user(django_user_model):
    username, password = "user2", "password"
    user = django_user_model.objects.create_user(username=username, password=password)
    user._password = password
    return user


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    [
        "deploy_progress",
        "deploy_state",
    ],
)
def test_get_user_not_authorized(client, domain, other_user, url_name):
    client.login(username=other_user.username, password=other_user._password)
    url = reverse(url_name, kwargs={"domain_id": domain.pk, "deployment_id": 1})
    r = client.get(url)
    assert r.status_code == 403


# def test_get_deployment_state_finished_has_stop_polling_status(client, domain):
#     user = domain.owner
#     client.login(username=user.username, password=user._password)
#     url = reverse("deploy_state", kwargs={"domain_id": domain.pk, "deployment_id": 1})
#     steps = [SpecialSteps.END.value]
#     with patch("apps.registry.models.Domain.get_new_steps", return_value=(steps, True)):
#         r = client.get(url)
#     assert r.status_code == 286


# def test_get_deployment_state_no_deployment_in_session(client, domain):
#     client.login(username=domain.owner.username, password=domain.owner._password)
#     url = reverse("deploy_state", kwargs={"domain_id": domain.pk, "deployment_id": 23})
#     r = client.get(url)
#     assert r.status_code == 404
