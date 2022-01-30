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


class Client(BaseModel):
    base_url: str = settings.DEPLOY_BASE_URL
    headers: dict = {"authorization": f"Bearer {settings.DEPLOY_SERVICE_TOKEN}"}

    def start_deployment(self) -> int:
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            r = client.post("deployments/")
        deployment_id = int(r.json()["id"])
        return deployment_id

    def fetch_deployment(self, deployment_id: int) -> Deployment:
        with httpx.Client(base_url=self.base_url, headers=self.headers) as client:
            r = client.get(f"deployments/{deployment_id}")
        deployment = Deployment(**r.json())
        deployment.steps.sort(reverse=True)
        return deployment


# def get_client():
#     print("settings deploy base url: ", settings.DEPLOY_BASE_URL)
#     base_url = settings.DEPLOY_BASE_URL
#     headers = {"authorization": f"Bearer {settings.DEPLOY_SERVICE_TOKEN}"}
#     return httpx.Client(headers=headers, base_url=base_url)
