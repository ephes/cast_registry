import pytest
from django.urls import reverse

from ..models import Domain


@pytest.mark.django_db
def test_get_register_not_authenticated(client):
    url = reverse("register")
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


@pytest.mark.django_db
def test_post_register_not_authenticated(client):
    url = reverse("register")
    r = client.post(url)
    assert r.status_code == 302
    assert "login" in r.url


def test_post_register_authenticated(client, user):
    client.login(username=user.username, password=user._password)
    url = reverse("register")
    r = client.post(url, data={"fqdn": "my.domain.staging.django-cast.com"})
    assert r.status_code == 302
    assert "deploy-progress" in r.url


@pytest.mark.django_db
def test_get_deploy_progress_not_authenticated(client):
    url = reverse("deploy_progress", kwargs={"domain_id": 1, "deployment_id": 1})
    r = client.get(url)
    assert r.status_code == 302
    assert "login" in r.url


@pytest.fixture
def domain(user):
    model = Domain.objects.create(fqdn="foo.staging.django-cast.com", owner=user)
    return model


@pytest.mark.django_db
def test_get_deploy_progress_authenticated(client, domain):
    user = domain.owner
    client.login(username=user.username, password=user._password)
    url = reverse("deploy_progress", kwargs={"domain_id": domain.pk, "deployment_id": 1})
    r = client.get(url)
    assert r.status_code == 200
    assert domain.fqdn in r.content.decode("utf8")
