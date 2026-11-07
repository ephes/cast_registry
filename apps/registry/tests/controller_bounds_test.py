"""Controller credentials and transfer budgets use only synthetic transports."""

import asyncio
import gzip
import json
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from django.core.exceptions import ImproperlyConfigured

from apps.registry.fastdeploy import ProductionClient, RemoteDeployment


def deployment():
    return SimpleNamespace(
        domain=SimpleNamespace(context={"database_password": "synthetic-password"}),
        service_token="synthetic-service-credential",
        remote=RemoteDeployment(id=1),
    )


@pytest.mark.parametrize("method", ["start_deployment", "fetch_deployment"])
@pytest.mark.parametrize(
    "url",
    [
        "/deploy/",
        "http://remote.example.test/",
        "https://user:synthetic@remote.example.test/",
        "https://@remote.example.test/",
        "https://remote.example.test/#fragment",
        "https://remote.example.test/#",
        "https://remote.example.test/?",
        "https://remote.example.test/?query=synthetic",
        "https://remote.example.test:bad/",
        "https:///missing",
        "https://remote.example.test\\@localhost/",
        "https://remote.example.test/\n",
        "ftp://remote.example.test/",
        "http://localhost.evil.test/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "https://remote.example.test:99999/",
        "https://remote.example.test:0/",
    ],
)
def test_unsafe_origin_rejected_before_credentials(method, url):
    factory = Mock(side_effect=AssertionError("Client must not be constructed"))
    with pytest.raises(ImproperlyConfigured) as exc:
        getattr(ProductionClient(base_url=url), method)(deployment(), client=factory)
    factory.assert_not_called()
    assert "synthetic" not in str(exc.value)
    assert url not in str(exc.value)


@pytest.mark.parametrize("method", ["start_deployment", "fetch_deployment"])
@pytest.mark.parametrize(
    "url",
    [
        "https://controller.example.test/",
        "https://controller.example.test/api/",
        "http://localhost:8000/",
        "http://127.0.0.1:8000/",
        "http://[::1]:8000/",
    ],
)
def test_safe_origin_and_explicit_loopback_development(method, url):
    seen = []

    def handle(request):
        seen.append(request)
        assert request.headers["authorization"] == "Bearer synthetic-service-credential"
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, stream=Stream([json.dumps({"id": 7}).encode()]))

    def factory(**kwargs):
        assert kwargs["follow_redirects"] is False
        return httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs)

    remote = getattr(ProductionClient(base_url=url, allow_loopback_http=True), method)(deployment(), client=factory)
    assert remote.id == 7
    assert len(seen) == 1


class Stream(httpx.AsyncByteStream):
    def __init__(self, chunks, drip=False):
        self.chunks = chunks
        self.drip = drip
        self.closed = False
        self.reads = 0

    async def __aiter__(self):
        for chunk in self.chunks:
            if self.drip:
                await asyncio.sleep(0.005)
            self.reads += 1
            yield chunk

    async def aclose(self):
        self.closed = True


@pytest.mark.parametrize("method", ["start_deployment", "fetch_deployment"])
@pytest.mark.parametrize("mode", ["oversize", "drip", "headers", "compressed", "json", "integer", "utf8"])
def test_transfer_limits_close_stream_and_hide_body(method, mode, caplog):
    stream = Stream([b"private-body" * 4] * 1000, drip=mode == "drip")
    if mode == "json":
        stream.chunks = [b"[" * 2000]
    if mode == "integer":
        stream.chunks = [b"1" * 5000]
    if mode == "utf8":
        stream.chunks = [b"\xff"]
    if mode == "compressed":
        stream.chunks = [gzip.compress(b"private-body" * 1000)]

    async def handle(request):
        if mode == "headers":
            await asyncio.sleep(10)
        headers = {"Content-Encoding": "gzip"} if mode == "compressed" else {}
        return httpx.Response(200, stream=stream, headers=headers)

    def factory(**kwargs):
        return httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs)

    controller = ProductionClient(base_url="https://controller.example.test/")
    controller.max_response_bytes = 100000 if mode in {"drip", "json", "integer"} else 32
    controller.exchange_timeout = 0.03
    with pytest.raises(httpx.HTTPError) as exc:
        getattr(controller, method)(deployment(), client=factory)
    if mode != "headers":
        assert stream.closed
    assert stream.reads < 1000
    assert "private-body" not in str(exc.value) + caplog.text


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("mode", ["oversize", "drip"])
def test_bounded_poll_preserves_snapshot_and_releases_lock(client, deployment, mode, caplog):
    from concurrent.futures import ThreadPoolExecutor
    from unittest.mock import patch

    from django.db import close_old_connections, connection
    from django.urls import reverse

    from apps.registry.models import Deployment

    deployment.data = RemoteDeployment(id=1, steps=[{"id": 1, "name": "saved evidence"}])
    deployment.save()
    original = deployment.data.model_dump(mode="json")
    stream = Stream([b"private-body" * 4] * 1000, drip=mode == "drip")

    def factory(**kwargs):
        return httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=stream)), **kwargs
        )

    controller = ProductionClient(base_url="https://controller.example.test/")
    controller.max_response_bytes = 100000 if mode == "drip" else 32
    controller.exchange_timeout = 0.03
    client.force_login(deployment.domain.owner)
    with patch(
        "apps.registry.fastdeploy.TestClient.fetch_deployment",
        side_effect=lambda attempt: controller.fetch_deployment(attempt, client=factory),
    ):
        response = client.get(reverse("deploy_state", args=[deployment.pk]))
    assert response.status_code == 200
    assert b"saved evidence" in response.content
    assert b"Progress unavailable" in response.content
    assert b"private-body" not in response.content
    assert "private-body" not in caplog.text
    deployment.refresh_from_db()
    assert deployment.data == original and deployment.last_updated is None
    assert stream.closed
    assert not connection.in_atomic_block

    # On PostgreSQL this is a separate connection, so a leaked row lock fails nowait.
    def acquire():
        from django.db import transaction

        close_old_connections()
        try:
            with transaction.atomic():
                return Deployment.objects.select_for_update(nowait=True).get(pk=deployment.pk).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(acquire).result(timeout=10) == deployment.pk


@pytest.mark.parametrize("method", ["start_deployment", "fetch_deployment"])
def test_development_override_does_not_allow_remote_http(method):
    factory = Mock()
    controller = ProductionClient(base_url="http://controller.example.test/", allow_loopback_http=True)
    with pytest.raises(ImproperlyConfigured):
        getattr(controller, method)(deployment(), client=factory)
    factory.assert_not_called()


def test_response_exactly_at_byte_budget_and_redirect_refused():
    calls = []
    payload = b'{"id":7}'
    controller = ProductionClient(base_url="https://controller.example.test/", headers={"X-Synthetic": "test"})
    controller.max_response_bytes = len(payload)

    def handle(request):
        calls.append(request)
        return httpx.Response(200, stream=Stream([payload[:3], payload[3:]]))

    def factory(**kwargs):
        return httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs)

    assert controller.fetch_deployment(deployment(), client=factory).id == 7

    def redirect(request):
        calls.append(request)
        return httpx.Response(302, headers={"Location": "http://remote.example.test/"})

    def redirect_factory(**kwargs):
        return httpx.AsyncClient(transport=httpx.MockTransport(redirect), **kwargs)

    with pytest.raises(httpx.HTTPStatusError):
        controller.fetch_deployment(deployment(), client=redirect_factory)
    assert len(calls) == 2
    assert all(request.url.host == "controller.example.test" for request in calls)


@pytest.mark.django_db
def test_configuration_failure_uses_safe_poll_path(client, deployment, settings):
    from unittest.mock import patch

    from django.urls import reverse

    deployment.data = RemoteDeployment(id=1)
    deployment.save()
    client.force_login(deployment.domain.owner)
    settings.DEPLOY_BASE_URL = "http://user:synthetic@remote.example.test/"
    with patch(
        "apps.registry.fastdeploy.TestClient.fetch_deployment",
        side_effect=lambda attempt: ProductionClient().fetch_deployment(attempt),
    ):
        response = client.get(reverse("deploy_state", args=[deployment.pk]))
    assert b"Progress unavailable" in response.content
    assert b"synthetic" not in response.content


@pytest.mark.parametrize("method", ["start_deployment", "fetch_deployment"])
def test_dns_executor_shutdown_does_not_extend_exchange_deadline(method, monkeypatch):
    import socket
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    resolving, release, returned = Event(), Event(), Event()

    def blocked_resolution(*args, **kwargs):
        resolving.set()
        assert release.wait(10)
        return []

    monkeypatch.setattr(socket, "getaddrinfo", blocked_resolution)

    async def handle(request):
        # This is the public resolver path used by HTTPX's async network backend.
        await asyncio.get_running_loop().getaddrinfo("synthetic.example.test", 443)
        raise AssertionError("Cancelled DNS must never proceed to send credentials")

    def factory(**kwargs):
        return httpx.AsyncClient(transport=httpx.MockTransport(handle), **kwargs)

    controller = ProductionClient(base_url="https://controller.example.test/")
    controller.exchange_timeout = 0.03

    def exchange():
        try:
            with pytest.raises(httpx.TimeoutException):
                getattr(controller, method)(deployment(), client=factory)
        finally:
            returned.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(exchange)
        try:
            assert resolving.wait(5)
            assert returned.wait(1), "Exchange joined a still-blocked native DNS worker"
            assert not release.is_set()
        finally:
            release.set()
        future.result(timeout=5)
