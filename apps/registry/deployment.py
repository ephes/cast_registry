import abc
import secrets
import string
from datetime import datetime
from enum import Enum

import httpx
from django.conf import settings
from pydantic import BaseModel


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
Finished = bool


class Deployment(BaseModel):
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

    def get_new_steps(self, seen: "Deployment") -> Steps:
        seen_steps = {s.id for s in seen.steps_for_client}
        return [s for s in self.steps_for_client if s.id not in seen_steps]


class DeploymentContext(BaseModel):
    env: dict = {}


class AbstractClient(abc.ABC):
    @abc.abstractmethod
    def start_deployment(self, domain) -> Deployment:
        raise NotImplementedError

    @abc.abstractmethod
    def fetch_deployment(self, deployment_id: int) -> Deployment:
        raise NotImplementedError


class ProductionClient(AbstractClient):
    def __init__(
        self,
        *,
        base_url: str = settings.DEPLOY_BASE_URL,
        headers: dict | None = None,
    ):
        self.base_url = base_url
        self.headers = headers
        if self.headers is None:
            self.headers = {"authorization": f"Bearer {settings.DEPLOY_SERVICE_TOKEN}"}

    @staticmethod
    def get_deployment_context(fqdn: str) -> DeploymentContext:
        alphabet = string.ascii_letters + string.digits
        database_password = "".join(secrets.choice(alphabet) for _ in range(20))
        secret_key = "".join(secrets.choice(alphabet) for _ in range(32))
        underscored_fqdn = fqdn.replace(".", "_")
        site_id = f"cast_{underscored_fqdn}"
        env = {
            "fqdn": fqdn,
            "site_id": site_id,
            "user_name": "cast_1",
            "database_name": site_id,
            "database_user": site_id,
            "database_password": database_password,
            "secret_key": secret_key,
            "port": 10001,
            "settings_file_name": site_id,
        }
        return DeploymentContext(env=env)

    def start_deployment(self, domain) -> Deployment:
        context = self.get_deployment_context(domain.fqdn)
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            r = client.post("deployments/", json=context.dict())
        deployment_id = int(r.json()["id"])
        return Deployment(id=deployment_id, no_steps_yet=True)

    def fetch_deployment(self, deployment_id: int) -> Deployment:
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            r = client.get(f"deployments/{deployment_id}")
        deployment = Deployment(**r.json())
        deployment.steps.sort(reverse=True)
        return deployment


class TestClient(AbstractClient):
    def start_deployment(self, domain) -> Deployment:
        return Deployment(id=1, no_steps_yet=True)

    def fetch_deployment(self, deployment_id: int) -> Deployment:
        return Deployment(service_id=1, origin="test", user="foo", steps=[])


Client: type[AbstractClient]
if settings.DEPLOY_CLIENT == "test":
    Client = TestClient
else:
    Client = ProductionClient
