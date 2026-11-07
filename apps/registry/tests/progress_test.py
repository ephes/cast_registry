from concurrent.futures import ThreadPoolExecutor
from json import JSONDecodeError
from threading import Barrier
from unittest.mock import patch

import httpx
import pytest
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from pydantic import ValidationError

from ..fastdeploy import RemoteDeployment, Step
from ..models import Deployment
from .models_test import StubClient


def initial(deployment):
    deployment.data = RemoteDeployment(id=1, no_steps_yet=True)
    deployment.save()


@pytest.mark.django_db
def test_viewers_receive_cumulative_history_and_terminal_snapshot(client, deployment):
    initial(deployment)
    client.force_login(deployment.domain.owner)
    other = Client()
    other.force_login(deployment.domain.owner)
    url = reverse("deploy_state", args=[deployment.pk])
    for viewer in [client, other]:
        assert b"Deployment Progress" in viewer.get(reverse("domain_deployments", args=[deployment.domain_id])).content
    first = RemoteDeployment(id=1, steps=[Step(id=1, name="download")])
    second = RemoteDeployment(id=1, steps=[Step(id=2, name="install")])
    final = RemoteDeployment(id=1, finished=timezone.now())
    with patch("apps.registry.fastdeploy.TestClient.fetch_deployment", side_effect=[first, second, final]) as fetch:
        a = client.get(url)
        b = other.get(url)
        assert b"download" in a.content
        assert b"download" in b.content and b"install" in b.content
        for viewer in [client, other, client, other]:
            response = viewer.get(url)
            assert response.status_code == 286
            assert response.content.count(b"<aside>download</aside>") == 1
            assert response.content.count(b"<aside>install</aside>") == 1
            assert response.content.count(b"Deployment is done!") == 1
            assert b"hx-trigger=" not in response.content
        assert fetch.call_count == 3
    deployment.refresh_from_db()
    assert deployment.last_updated is not None


@pytest.mark.django_db
def test_stale_instance_cannot_erase_progress(deployment):
    initial(deployment)
    stale = Deployment.objects.get(pk=deployment.pk)
    deployment.refresh_progress(StubClient(RemoteDeployment(id=1, steps=[Step(id=1, name="download")])))
    stale.refresh_progress(StubClient(RemoteDeployment(id=1, steps=[Step(id=2, name="install")])))
    deployment.refresh_from_db()
    assert [s.name for s in deployment.progress_steps] == ["Starting deployment...", "download", "install"]
    # Legacy names without remote IDs remain independently visible.
    deployment.processed_steps = [{"name": "legacy one"}, {"name": "legacy two"}]
    assert {"legacy one", "legacy two"} <= {s.name for s in deployment.progress_steps}


@pytest.mark.django_db(transaction=True)
def test_concurrent_viewers_publish_without_lost_history(deployment):
    if not connection.features.has_select_for_update:
        pytest.skip("Row-lock regression requires PostgreSQL; exercised by both CI jobs")
    initial(deployment)
    barrier = Barrier(2)
    pk = deployment.pk

    def poll(step_id):
        close_old_connections()
        try:
            viewer = Deployment.objects.get(pk=pk)
            barrier.wait(timeout=10)
            viewer.refresh_progress(
                StubClient(RemoteDeployment(id=1, steps=[Step(id=step_id, name=f"step {step_id}")]))
            )
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(poll, [1, 2]))
    deployment.refresh_from_db()
    assert {s.name for s in deployment.progress_steps} == {"Starting deployment...", "step 1", "step 2"}


@pytest.mark.django_db
@pytest.mark.parametrize(
    "failure", [httpx.ConnectError("private connection detail"), httpx.ReadTimeout("private timeout")]
)
def test_failed_start_is_safe_durable_and_retry_is_new_attempt(client, domain, failure, caplog):
    client.force_login(domain.owner)
    url = reverse("domain_deployments", args=[domain.pk])
    with patch("apps.registry.fastdeploy.TestClient.start_deployment", side_effect=failure) as start:
        response = client.post(url, {"target": "RM"}, follow=True)
        assert start.call_count == 1
    failed = Deployment.objects.get(domain=domain)
    assert f"Start unconfirmed for deployment {failed.pk}" in caplog.text
    assert "private" not in caplog.text
    assert failed.start_failed and not failed.in_progress
    assert failed.data is None
    for response in [response, client.get(url)]:
        assert b"Start could not be confirmed" in response.content
        assert b"private" not in response.content
        assert b'hx-trigger="every' not in response.content
        assert b"?target=RM#deployment-form" in response.content
    prepared = client.get(url + "?target=RM")
    assert prepared.context["form"].initial["target"] == "RM"
    assert Deployment.objects.count() == 1
    assert client.get(url + "?target=bad").context["form"].initial["target"] == "DP"
    with patch("apps.registry.fastdeploy.TestClient.start_deployment", return_value=RemoteDeployment(id=2)) as start:
        client.post(url, {"target": "RM", "reconciled_attempts": [failed.pk]})
        assert start.call_count == 1
    failed.refresh_from_db()
    assert failed.start_failed
    assert Deployment.objects.count() == 2
    assert not Deployment.objects.latest("pk").start_failed


@pytest.mark.django_db
@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("private error"),
        JSONDecodeError("private JSON", "", 0),
        ValidationError.from_exception_data("RemoteDeployment", []),
        httpx.HTTPStatusError(
            "private status", request=httpx.Request("GET", "https://example.invalid"), response=httpx.Response(503)
        ),
    ],
)
def test_poll_failure_preserves_evidence_and_recovers(client, deployment, failure, caplog):
    initial(deployment)
    client.force_login(deployment.domain.owner)
    url = reverse("deploy_state", args=[deployment.pk])
    first = RemoteDeployment(id=1, steps=[Step(id=1, name="download")])
    final = RemoteDeployment(id=1, steps=[Step(id=2, name="install")], finished=timezone.now())
    with patch("apps.registry.fastdeploy.TestClient.fetch_deployment", side_effect=[first, failure, final]):
        assert b"download" in client.get(url).content
        deployment.refresh_from_db()
        last_updated = deployment.last_updated
        response = client.get(url)
        assert response.status_code == 200
        assert b"<aside>download</aside>" in response.content
        assert b'role="alert"' in response.content
        assert f"Progress refresh unavailable for deployment {deployment.pk}" in caplog.text
        assert "private" not in caplog.text
        assert b"Refresh progress" in response.content
        assert b"private" not in response.content
        assert b"hx-trigger=" not in response.content
        deployment.refresh_from_db()
        assert deployment.last_updated == last_updated
        assert not deployment.has_finished
        response = client.get(url)
        assert response.status_code == 286
        assert b"<aside>download</aside>" in response.content
        assert b"<aside>install</aside>" in response.content
        assert b"Progress unavailable" not in response.content


@pytest.mark.django_db
def test_unstarted_progress_does_not_call_controller(client, deployment):
    client.force_login(deployment.domain.owner)
    with patch("apps.registry.fastdeploy.TestClient.fetch_deployment") as fetch:
        response = client.get(reverse("deploy_state", args=[deployment.pk]))
    assert response.status_code == 200
    assert not fetch.called
