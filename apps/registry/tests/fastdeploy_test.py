from datetime import timedelta

import httpx
import pytest
from django.utils import timezone

from ..fastdeploy import ProductionClient, RemoteDeployment, SpecialSteps, Step

NEW = Step(id=2, name="new")
NOT_NEW = Step(id=2, name="not new")


@pytest.mark.parametrize(
    "deployment, seen, expected",
    [
        (
            RemoteDeployment(),
            RemoteDeployment(no_steps_yet=True),
            [SpecialSteps.START.value],
        ),  # no deployment seen before
        (
            RemoteDeployment(finished=timezone.now()),
            RemoteDeployment(),
            [SpecialSteps.END.value],
        ),  # only finished step
        (RemoteDeployment(steps=[NEW]), RemoteDeployment(), [NEW]),  # new step
        (RemoteDeployment(steps=[NOT_NEW]), RemoteDeployment(steps=[NOT_NEW]), []),  # no new step -> []
    ],
)
def test_get_new_step(deployment, seen, expected):
    assert deployment.get_new_steps(seen) == expected


def test_sort_steps():
    start_none = Step(name="start_none", started=None)
    start_now = Step(name="start_none", started=timezone.now())
    assert [start_none, start_now] == sorted([start_none, start_now])
    assert [start_none, start_now] == sorted([start_now, start_none])

    start_later = Step(name="start_later", started=timezone.now() + timedelta(minutes=2))
    assert [start_now, start_later] == sorted([start_later, start_now])
    assert [start_none, start_none] == sorted([start_none, start_none])


class Response:
    def __init__(self, status_code, json={"foo": "bar", "id": 1}):
        self.status_code = status_code
        self.json_data = json

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code == 401:
            raise Exception("not authorized")


class OkHttpxClient(httpx.Client):
    def get(self, path):
        return Response(200)

    def post(self, path, json={}):
        return Response(200)


class BrokenHttpxClient(httpx.Client):
    def get(self, path):
        return Response(401)

    def post(self, path, json={}):
        return Response(401, json={"detail": "Could not validate credentials"})


class Remote:
    def __init__(self, deployment_id):
        self.id = deployment_id


class Deployment:
    def __init__(self, deployment_id):
        self.remote = Remote(deployment_id)
        self.service_token = "asdf"


class Domain:
    def __init__(self):
        self.context = {}


def test_production_client_fetch_deployment_broken():
    """Response status is not ok"""
    client = ProductionClient()
    deployment = Deployment(1)
    fetched_deployment = client.fetch_deployment(deployment, client=BrokenHttpxClient)
    assert isinstance(fetched_deployment, Remote)


def test_production_client_fetch_deployment_ok():
    """Response status is ok"""
    client = ProductionClient()
    deployment = Deployment(1)
    fetched_deployment = client.fetch_deployment(deployment, client=OkHttpxClient)
    assert isinstance(fetched_deployment, RemoteDeployment)


def test_production_client_start_deployment_unauthorized():
    client = ProductionClient()
    deployment = Deployment(1)
    deployment.domain = Domain()
    with pytest.raises(Exception):
        client.start_deployment(deployment, client=BrokenHttpxClient)


def test_production_client_start_deployment():
    """Start deployment test, mainly for coverage"""
    client = ProductionClient()
    deployment = Deployment(1)
    deployment.domain = Domain()
    started_deployment = client.start_deployment(deployment, client=OkHttpxClient)
    assert isinstance(started_deployment, RemoteDeployment)


def test_getting_production_client(settings):
    from apps.registry.fastdeploy import ProductionClient, TestClient

    settings.DEPLOY_CLIENT = "test"
    from apps.registry.fastdeploy import Client

    assert isinstance(Client, type(TestClient))
    settings.DEPLOY_CLIENT = "asdf"
    from apps.registry.fastdeploy import Client

    assert isinstance(Client, type(ProductionClient))
