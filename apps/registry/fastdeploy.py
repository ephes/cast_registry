import abc
import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Deployment  # pragma: no cover

import httpx
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Step(BaseModel):
    id: int | None = None
    name: str
    started: datetime | None = None
    finished: datetime | None = None
    state: str = "pending"
    message: str = ""

    def __lt__(self, other):
        """Sort by started datetime, reverse"""
        if self.started is not None:
            if other.started is None:
                # self datetime, other None
                return False
            else:
                # self datetime, other datetime
                return self.started < other.started
        else:
            if other.started is None:
                # both None
                return True
            else:
                # self None, other datetime
                return True


class SpecialSteps(Enum):
    START = Step(id=0, name="Starting deployment...")
    END = Step(id=-1, name="Deployment is done!")


Steps = list[Step]


class RemoteDeployment(BaseModel):
    id: int | None = None
    steps: Steps = []
    service_id: int = 1
    origin: str = "test"
    user: str = "test"
    started: datetime | None = None
    finished: datetime | None = None
    context: dict = {}
    no_steps_yet: bool = False  # used to signal that self was just started

    @property
    def has_finished(self):
        return self.finished is not None

    @property
    def steps_for_client(self):
        if self.no_steps_yet:
            return []
        steps = [SpecialSteps.START.value]
        steps.extend(self.steps)
        if self.has_finished:
            steps.append(SpecialSteps.END.value)
        return steps

    def get_new_steps(self, seen: "RemoteDeployment") -> Steps:
        seen_steps = {s.id for s in seen.steps_for_client}
        return [s for s in self.steps_for_client if s.id not in seen_steps]


class DeploymentContext(BaseModel):
    env: dict = {}


class AbstractClient(abc.ABC):
    @abc.abstractmethod
    def start_deployment(self, deployment: "Deployment") -> RemoteDeployment:
        raise NotImplementedError  # pragma: no cover

    @abc.abstractmethod
    def fetch_deployment(self, deployment: "Deployment") -> RemoteDeployment:
        raise NotImplementedError  # pragma: no cover


class ProductionClient(AbstractClient):
    def __init__(
        self,
        *,
        base_url: str = settings.DEPLOY_BASE_URL,
        headers: dict = {},
    ):
        self.base_url = base_url
        self.headers = headers

    def start_deployment(self, deployment, client=httpx.Client) -> RemoteDeployment:
        domain = deployment.domain
        context = DeploymentContext(env=domain.context)
        headers = self.headers | {"authorization": f"Bearer {deployment.service_token}"}
        with client(base_url=self.base_url, headers=headers) as client:
            r = client.post("deployments/", json=context.model_dump())
        if r.status_code > 400:
            logger.error(f"start deploy request status is: {r.status_code}")
            logger.error(f"response details: {r.json()['detail']}")
        r.raise_for_status()
        deployment_id = int(r.json()["id"])
        return RemoteDeployment(id=deployment_id, no_steps_yet=True)

    def fetch_deployment(self, deployment, client=httpx.Client) -> RemoteDeployment:
        deployment_id = deployment.remote.id
        assert isinstance(deployment_id, int)
        headers = self.headers | {"authorization": f"Bearer {deployment.service_token}"}
        print("base url: ", self.base_url)
        with client(base_url=self.base_url, headers=headers) as client:
            r = client.get(f"deployments/{deployment_id}")
        if r.status_code != 200:
            return deployment.remote
        remote_deployment = RemoteDeployment(**r.json())
        remote_deployment.steps.sort(reverse=True)
        return remote_deployment


def create_test_deployments():
    deployments = [RemoteDeployment(id=1, no_steps_yet=True)]
    step_names = ["first step", "second step"]
    for step_id, step_name in enumerate(step_names, 1):
        steps = [Step(id=step_id, name=step_name)]
        deployments.append(RemoteDeployment(service_id=1, origin="test", user="foo", steps=steps))
    deployments.append(RemoteDeployment(service_id=1, finished=timezone.now()))
    deployments.reverse()
    return deployments


TEST_DEPLOYMENTS: dict[int, list] = {}


class TestClient(AbstractClient):
    """
    Use the same TEST_DEPLOYMENTS dict for all test clients.
    """

    def __init__(self):
        global TEST_DEPLOYMENTS
        self.global_deployments = TEST_DEPLOYMENTS

    def start_deployment(self, deployment) -> RemoteDeployment:
        self.global_deployments[deployment.pk] = create_test_deployments()
        deployment = self.global_deployments[deployment.pk].pop()
        return deployment

    def fetch_deployment(self, deployment) -> RemoteDeployment:  # pragma: no cover
        return self.global_deployments[deployment.pk].pop()


Client: type[AbstractClient]
if settings.DEPLOY_CLIENT == "test":  # pragma: no cover
    Client = TestClient
else:  # pragma: no cover
    Client = ProductionClient
