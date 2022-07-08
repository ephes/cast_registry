from django.utils import timezone

from ..deployment import Deployment, SpecialSteps


class StubClient:
    def __init__(self, deployment):
        self.deployment = deployment

    def start_deployment(self, _):
        return self.deployment

    def fetch_deployment(self, _):
        return self.deployment


def test_domain_start_deployment_puts_deployment_in_session(domain):
    session = {}
    deployment = Deployment(id=1, no_steps_yet=True)
    _ = domain.start_deployment(session, client=StubClient(deployment))
    assert list(session.values()) == [deployment.json()]


def test_get_new_steps(domain):
    deployment = Deployment(id=1, no_steps_yet=True)
    session = {domain.get_session_key_from_deployment_id(deployment.id): deployment.json()}
    deployment.no_steps_yet = False
    new_steps, finished = domain.get_new_steps(session, deployment.id, client=StubClient(deployment))
    assert new_steps == [SpecialSteps.START.value]
    assert not finished
    assert list(session.values()) == [deployment.json()]

    # start step is already seen
    new_steps, finished = domain.get_new_steps(session, deployment.id, client=StubClient(deployment))
    assert new_steps == []


def test_finished_deployment_is_removed_from_session(domain):
    deployment = Deployment(id=1, finished=timezone.now())
    deployment_key = domain.get_session_key_from_deployment_id(deployment.id)
    session = {deployment_key: deployment.json()}
    new_steps, finished = domain.get_new_steps(session, deployment.id, client=StubClient(deployment))
    assert finished
    assert list(session.values()) == []
