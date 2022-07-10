import pytest

from ..fastdeploy import RemoteDeployment, SpecialSteps
from ..models import Deployment

# Tests for Deployment model


class StubClient:
    def __init__(self, deployment):
        self.deployment = deployment

    def start_deployment(self, _):
        return self.deployment

    def fetch_deployment(self, _):
        return self.deployment


@pytest.mark.django_db
def test_deployment_remote_serialization(domain, remote_deployment):
    deployment = Deployment(domain=domain)
    deployment.save()
    deployment.refresh_from_db()
    assert deployment.data is None
    deployment.data = remote_deployment
    deployment.save()
    deployment.refresh_from_db()
    assert deployment.remote == remote_deployment


@pytest.mark.django_db
def test_deployment_start(domain, remote_deployment):
    deployment = Deployment(domain=domain)
    client = StubClient(remote_deployment)
    deployment.start(client=client)
    deployment.save()
    deployment.refresh_from_db()
    assert deployment.remote == remote_deployment


@pytest.mark.django_db
def test_deployment_get_new_steps(domain):
    remote_deployment = RemoteDeployment(id=1, no_steps_yet=True)
    deployment = Deployment(domain=domain, data=remote_deployment)
    deployment.save()
    deployment.refresh_from_db()
    remote_deployment.no_steps_yet = False
    client = StubClient(remote_deployment)
    new_steps = deployment.get_new_steps(client=client)
    assert new_steps == [SpecialSteps.START.value]
    assert not deployment.remote.has_finished

    # start step is already seen
    deployment.refresh_from_db()
    new_steps = deployment.get_new_steps(client=client)
    assert new_steps == []