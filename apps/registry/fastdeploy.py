import abc
import asyncio
import ipaddress
import json
import logging
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from urllib.parse import urlsplit

if TYPE_CHECKING:
    from .models import Deployment  # pragma: no cover

import httpx
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
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
    max_response_bytes = 1024 * 1024
    exchange_timeout = 10.0

    def __init__(
        self, *, base_url: str | None = None, headers: dict | None = None, allow_loopback_http: bool | None = None
    ):
        self.base_url = settings.DEPLOY_BASE_URL if base_url is None else base_url
        self.headers = {} if headers is None else headers
        self.allow_loopback_http = (
            settings.DEPLOY_ALLOW_LOOPBACK_HTTP if allow_loopback_http is None else allow_loopback_http
        )

    def validate_base_url(self):
        """Reject unsafe configuration before constructing credential-bearing requests."""
        try:
            if any(ord(char) <= 32 or ord(char) >= 127 for char in self.base_url) or "\\" in self.base_url:
                raise ValueError
            URLValidator(schemes=["http", "https"])(self.base_url)
            parts = urlsplit(self.base_url)
            if (
                parts.username is not None
                or parts.password is not None
                or "#" in self.base_url
                or "?" in self.base_url
            ):
                raise ValueError
            if parts.port is not None and not 1 <= parts.port <= 65535:
                raise ValueError
            if parts.scheme == "http":
                host = parts.hostname
                assert host is not None
                try:
                    loopback = ipaddress.ip_address(host).is_loopback
                except ValueError:
                    loopback = host == "localhost"
                if not self.allow_loopback_http or not loopback:
                    raise ValueError
        except (ValueError, DjangoValidationError):
            raise ImproperlyConfigured(
                "DEPLOY_BASE_URL must be an absolute HTTPS URL without userinfo, query or fragment. "
                "Loopback HTTP requires DEPLOY_ALLOW_LOOPBACK_HTTP for local development."
            ) from None

    async def request_json(self, method, path, headers, client, payload=None):
        try:
            # Async cancellation covers headers and drip-fed bodies, not just individual reads.
            async with asyncio.timeout(self.exchange_timeout):
                async with client(
                    base_url=self.base_url,
                    headers=headers | {"Accept-Encoding": "identity"},
                    follow_redirects=False,
                    timeout=self.exchange_timeout,
                ) as http:
                    async with http.stream(method, path, json=payload) as response:
                        response.raise_for_status()
                        if response.headers.get("content-encoding", "identity").lower() != "identity":
                            raise httpx.DecodingError("Controller response must use identity encoding")
                        body = bytearray()
                        async for chunk in response.aiter_raw():
                            if len(body) + len(chunk) > self.max_response_bytes:
                                raise httpx.DecodingError("Controller response byte limit exceeded")
                            body.extend(chunk)
                        try:
                            return json.loads(body)
                        except (ValueError, RecursionError):
                            raise httpx.DecodingError("Invalid controller JSON response") from None
        except TimeoutError:
            raise httpx.TimeoutException("Controller exchange time limit exceeded") from None

    def exchange(self, *args):
        # loop.close() shuts down its executor without joining an uncancellable
        # native DNS lookup. asyncio.run() joins it, extending the request/row lock.
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.request_json(*args))
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            finally:
                loop.close()

    def start_deployment(self, deployment, client=httpx.AsyncClient) -> RemoteDeployment:
        self.validate_base_url()
        context = DeploymentContext(env=deployment.domain.context)
        headers = self.headers | {"authorization": f"Bearer {deployment.service_token}"}
        try:
            result = self.exchange("POST", "deployments/", headers, client, context.model_dump())
        except httpx.HTTPStatusError as exc:
            logger.error("start deploy request status is: %s", exc.response.status_code)
            raise
        deployment_id = int(result["id"])
        return RemoteDeployment(id=deployment_id, no_steps_yet=True)

    def fetch_deployment(self, deployment, client=httpx.AsyncClient) -> RemoteDeployment:
        self.validate_base_url()
        deployment_id = deployment.remote.id
        assert isinstance(deployment_id, int)
        headers = self.headers | {"authorization": f"Bearer {deployment.service_token}"}
        result = self.exchange("GET", f"deployments/{deployment_id}", headers, client)
        remote_deployment = RemoteDeployment.model_validate(result)
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
