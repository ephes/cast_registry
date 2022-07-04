import secrets
import string
from datetime import datetime

import httpx
from django.conf import settings
from pydantic import BaseModel


class Step(BaseModel):
    id: int | None
    name: str
    started: datetime | None
    finished: datetime | None
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


class Deployment(BaseModel):
    id: int | None
    steps: list[Step] = []
    service_id: int
    origin: str
    user: str
    started: datetime | None
    finished: datetime | None
    context: dict = {}


class DeploymentContext(BaseModel):
    env: dict = {}


class ProductionClient(BaseModel):
    base_url: str = settings.DEPLOY_BASE_URL
    headers: dict = {"authorization": f"Bearer {settings.DEPLOY_SERVICE_TOKEN}"}

    @staticmethod
    def get_deployment_context(fqdn: str) -> DeploymentContext:
        alphabet = string.ascii_letters + string.digits
        database_password = "".join(secrets.choice(alphabet) for i in range(20))
        secret_key = "".join(secrets.choice(alphabet) for i in range(32))
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

    def start_deployment(self, domain) -> int:
        context = self.get_deployment_context(domain.fqdn)
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            r = client.post("deployments/", json=context.dict())
        deployment_id = int(r.json()["id"])
        return deployment_id

    def fetch_deployment(self, deployment_id: int) -> Deployment:
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            r = client.get(f"deployments/{deployment_id}")
        deployment = Deployment(**r.json())
        deployment.steps.sort(reverse=True)
        return deployment


class TestClient:
    @staticmethod
    def get_deployment_context(fqdn: str) -> DeploymentContext:
        return {}

    def start_deployment(self, domain) -> int:
        return 1

    def fetch_deployment(self, deployment_id) -> Deployment:
        return Deployment({})


if settings.DEPLOY_CLIENT == "test":
    Client = TestClient
else:
    Client = ProductionClient


# def get_client():
#     print("settings deploy base url: ", settings.DEPLOY_BASE_URL)
#     base_url = settings.DEPLOY_BASE_URL
#     headers = {"authorization": f"Bearer {settings.DEPLOY_SERVICE_TOKEN}"}
#     return httpx.Client(headers=headers, base_url=base_url)
