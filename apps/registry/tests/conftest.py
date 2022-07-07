import pytest

from ..models import Domain


@pytest.fixture
def user(django_user_model):
    username, password = "user1", "password"
    user = django_user_model.objects.create_user(username=username, password=password)
    user._password = password
    return user


@pytest.fixture
def domain(user):
    model = Domain.objects.create(fqdn="foo.staging.django-cast.com", owner=user)
    return model
