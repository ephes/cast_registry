import pytest
from django.urls import reverse
from django.utils import timezone

from ..deployment import Deployment
from ..views import Messages, get_deployment_state_response


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method, url",
    [
        ("get", reverse("register")),
        ("post", reverse("register")),
        ("get", reverse("deploy_progress", kwargs={"domain_id": 1, "deployment_id": 1})),
        ("get", reverse("deploy_state", kwargs={"domain_id": 1, "deployment_id": 1})),
    ],
)
def test_get_login_required_not_authenticated(client, method, url):
    r = client.get(url)
    assert r.status_code == 302
    assert "login" in r.url


@pytest.mark.django_db
def test_get_register_authenticated(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("register")
    r = client.get(url)
    assert r.status_code == 200
    assert "form action" in r.content.decode("utf8")


def test_post_register_authenticated(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("register")
    r = client.post(url, data={"fqdn": "my.domain.staging.django-cast.com"})
    assert r.status_code == 302
    assert "deploy-progress" in r.url


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name, test_content",
    [
        ("deploy_progress", "staging.django-cast.com"),
        ("deploy_state", "aside"),
    ],
)
def test_get_login_required_with_domain_authenticated(client, domain, url_name, test_content):
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse(url_name, kwargs={"domain_id": domain.pk, "deployment_id": 1})
    r = client.get(url)
    assert r.status_code == 200
    assert test_content in r.content.decode("utf8")


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


@pytest.fixture
def deployment_params():
    return dict(service_id=1, origin="registry", user="user1")


def test_get_deployment_state_response_starting(deployment_params):
    deployment = Deployment(**deployment_params)
    response, sent = get_deployment_state_response(deployment, [])
    assert response.status_code == 200
    assert [Messages.START.value] == sent


def test_get_deployment_state_response_finished(deployment_params):
    deployment = Deployment(**deployment_params, finished=timezone.now())
    response, sent = get_deployment_state_response(deployment, [Messages.START.value])
    assert response.status_code == 286
    assert [Messages.END.value] == sent


def test_get_deployment_state_response_new_step(deployment_params):
    new = "new step"
    deployment = Deployment(**deployment_params, steps=[{"name": new}])
    response, sent = get_deployment_state_response(deployment, [Messages.START.value])
    assert response.status_code == 200
    assert [new] == sent


def test_get_deployment_state_response_no_new_step(deployment_params):
    seen = "seen step"
    deployment = Deployment(**deployment_params, steps=[{"name": seen}])
    response, sent = get_deployment_state_response(deployment, [Messages.START.value, seen])
    assert response.status_code == 200
    assert [] == sent
