import pytest
from django.urls import reverse

from ..models import Domain


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


@pytest.fixture
def user(django_user_model):
    username, password = "user1", "password"
    user = django_user_model.objects.create_user(username=username, password=password)
    user._password = password
    return user


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


@pytest.fixture
def domain(user):
    model = Domain.objects.create(fqdn="foo.staging.django-cast.com", owner=user)
    return model


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
