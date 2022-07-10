from datetime import datetime

import pytest

from ..fastdeploy import RemoteDeployment, Step
from ..models import Deployment, Domain


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


@pytest.fixture
def deployment(domain):
    deployment = Deployment.objects.create(domain=domain)
    return deployment


@pytest.fixture
def remote_deployment():
    """
    Use datetime without microseconds instead of timezone.now() because
    Django strips microseconds from timestamps it serializes to json
    because of ECMA-262 and the assertion would fail.
    """
    started = datetime(2022, 7, 22, 9)
    step = Step(name="step name", started=started)
    return RemoteDeployment(id=1, service_id=1, origin="registry", user="user1", steps=[step])
