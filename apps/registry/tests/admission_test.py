"""Synthetic security regressions through forms, context and real POST admission."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

import httpx
import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from ..fastdeploy import RemoteDeployment
from ..forms import DomainForm
from ..models import Deployment, Domain

INVALID_DOMAINS = [
    "example.test/../../outside",
    "example.test\n",
    " example.test",
    "example.test ",
    "example.test;id",
    "example.test$(id)",
    "https://example.test",
    "user@example.test",
    "example.test:443",
    "foo_bar.test",
    "café.test",
    "-bad.example.test",
    "Podcast.Example.Test",
    "podcast.example.test.",
    "10.0.0.10",
    "x" * 63 + "." + "y" * 63 + "." + "z" * 63 + "." + "a" * 63,
]


@pytest.mark.django_db
@pytest.mark.parametrize("fqdn", INVALID_DOMAINS)
def test_domain_input_and_legacy_rows_fail_before_controller(client, user, fqdn):
    assert not DomainForm({"fqdn": fqdn, "backend": "CA"}).is_valid()
    client.force_login(user)
    with patch("apps.registry.fastdeploy.TestClient.start_deployment") as start:
        response = client.post(reverse("domains"), {"fqdn": fqdn, "backend": "CA"})
        assert response.status_code == 200
        assert not Domain.objects.exists()
        # ORM writes bypass validation: existing invalid rows must still be safe.
        domain = Domain.objects.create(fqdn=fqdn, owner=user)
        with pytest.raises(ValidationError):
            _ = domain.context
        response = client.post(reverse("domain_deployments", args=[domain.pk]), {"target": "DP"})
        assert response.status_code == 200
        assert not Deployment.objects.exists()
        start.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("fqdn", ["podcast.example.test", "a-b.example.test", "xn--caf-dma.example.test"])
def test_safe_domain_identifiers(fqdn, user):
    form = DomainForm({"fqdn": fqdn, "backend": "CA"})
    assert form.is_valid()
    domain = form.save(commit=False)
    domain.owner = user
    domain.save()
    assert domain.context["site_id"] == "cast_" + fqdn.replace(".", "_")
    assert domain.context["fqdn"] == fqdn


@pytest.mark.django_db
@pytest.mark.parametrize("target", ["DP", "RM"])
@pytest.mark.parametrize("state", ["pending", "running", "unconfirmed"])
def test_pending_running_and_uncertain_attempts_block(client, domain, target, state):
    data = RemoteDeployment(id=1) if state == "running" else None
    old = Deployment.objects.create(domain=domain, data=data, start_failed=state == "unconfirmed")
    client.force_login(domain.owner)
    with patch("apps.registry.fastdeploy.TestClient.start_deployment") as start:
        response = client.post(reverse("domain_deployments", args=[domain.pk]), {"target": target})
        assert response.status_code == 409
        assert b"active or unconfirmed" in response.content
        start.assert_not_called()
    assert list(Deployment.objects.values_list("pk", flat=True)) == [old.pk]


@pytest.mark.django_db
def test_explicit_reconciliation_only_releases_selected_uncertain_attempt(client, domain):
    old = Deployment.objects.create(domain=domain, start_failed=True)
    client.force_login(domain.owner)
    url = reverse("domain_deployments", args=[domain.pk])
    with patch("apps.registry.fastdeploy.TestClient.start_deployment", side_effect=httpx.ReadTimeout("synthetic")):
        assert client.post(url, {"target": "DP", "reconciled_attempts": [old.pk]}).status_code == 302
    old.refresh_from_db()
    assert old.start_failed and old.reconciled
    # Replaying the same acknowledgement cannot reconcile the new uncertain start.
    with patch("apps.registry.fastdeploy.TestClient.start_deployment") as start:
        assert client.post(url, {"target": "RM", "reconciled_attempts": [old.pk]}).status_code == 200
        assert client.post(url, {"target": "RM"}).status_code == 409
        start.assert_not_called()
    assert Deployment.objects.count() == 2


@pytest.mark.django_db
def test_completed_and_other_domain_attempts_do_not_block(client, domain):
    Deployment.objects.create(domain=domain, data=RemoteDeployment(id=1, finished=timezone.now()))
    other = Domain.objects.create(owner=domain.owner, fqdn="other.example.test")
    Deployment.objects.create(domain=other)
    client.force_login(domain.owner)
    with patch("apps.registry.fastdeploy.TestClient.start_deployment", return_value=RemoteDeployment(id=2)) as start:
        assert client.post(reverse("domain_deployments", args=[domain.pk]), {"target": "RM"}).status_code == 302
        start.assert_called_once()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("targets", [("DP", "DP"), ("DP", "RM")])
def test_two_clients_admit_exactly_one_before_remote_completion(domain, targets):
    if not connection.features.has_select_for_update:
        pytest.skip("Admission serialization requires PostgreSQL; both CI jobs exercise it")
    clients = [Client(), Client()]
    for client in clients:
        client.force_login(domain.owner)
    barrier, called, rejected = Barrier(2), Event(), Event()
    url = reverse("domain_deployments", args=[domain.pk])

    def remote_start(deployment):
        # The admission is committed and visible before the controller is invoked.
        assert Deployment.objects.filter(pk=deployment.pk, data=None).exists()
        called.set()
        assert rejected.wait(10)
        return RemoteDeployment(id=1)

    def submit(i):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            response = clients[i].post(url, {"target": targets[i]})
            if response.status_code == 409:
                assert called.wait(10)
                rejected.set()
            return response.status_code
        finally:
            close_old_connections()

    with patch("apps.registry.fastdeploy.TestClient.start_deployment", side_effect=remote_start) as start:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert sorted(pool.map(submit, [0, 1])) == [302, 409]
        start.assert_called_once()
    assert Deployment.objects.filter(domain=domain).count() == 1
