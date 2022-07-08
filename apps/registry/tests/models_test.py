from django.utils import timezone

from ..deployment import Deployment, SpecialSteps


def test_domain_start_deployment(domain):
    deployment_id = domain.start_deployment()
    assert deployment_id == 1


class StubClient:
    def __init__(self, deployment):
        self.deployment = deployment

    def fetch_deployment(self, _):
        return self.deployment


def test_get_new_steps(domain):
    session = {}
    deployment = Deployment(id=1)
    new_steps, finished = domain.get_new_steps(session, deployment.id, client=StubClient(deployment))
    assert new_steps == [SpecialSteps.START.value]
    assert not finished
    assert list(session.values()) == [deployment.json()]

    # start step is already seen
    new_steps, finished = domain.get_new_steps(session, deployment.id, client=StubClient(deployment))
    assert new_steps == []


def test_finished_deployment_is_removed_from_session(domain):
    deployment = Deployment(id=1, finished=timezone.now())
    deployment_key = f"deployment_{deployment.id}"
    session = {deployment_key: deployment.json()}
    new_steps, finished = domain.get_new_steps(session, deployment.id, client=StubClient(deployment))
    assert finished
    assert list(session.values()) == []
