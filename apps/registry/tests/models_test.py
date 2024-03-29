import pytest
from django.conf import settings

from ..fastdeploy import RemoteDeployment, SpecialSteps
from ..models import Deployment, Domain

# Tests for Domain model


def test_domain_get_service_token():
    domain = Domain(backend=Domain.Backend.CAST)
    service_tokens = domain.service_tokens
    assert "deploy" in service_tokens
    assert "remove" in service_tokens

    domain = Domain(backend="foo")
    assert domain.service_tokens == {}


# Tests for Deployment model


class StubClient:
    def __init__(self, deployment):
        self.deployment = deployment

    def start_deployment(self, _):
        return self.deployment

    def fetch_deployment(self, _):
        return self.deployment


@pytest.mark.django_db
def test_deployment_remote_serialization(domain, remote_deployment):
    deployment = Deployment(domain=domain)
    deployment.save()
    deployment.refresh_from_db()
    assert deployment.data is None
    deployment.data = remote_deployment
    deployment.save()
    deployment.refresh_from_db()
    assert deployment.remote == remote_deployment


@pytest.mark.django_db
def test_deployment_start(domain, remote_deployment):
    deployment = Deployment(domain=domain)
    client = StubClient(remote_deployment)
    deployment.start(client=client)
    deployment.save()
    deployment.refresh_from_db()
    assert deployment.remote == remote_deployment


@pytest.mark.django_db
def test_deployment_get_empty_new_steps_on_finished(finished_deployment):
    new_steps = finished_deployment.get_new_steps()
    assert new_steps == []


@pytest.mark.django_db
def test_deployment_get_new_steps(domain):
    remote_deployment = RemoteDeployment(id=1, no_steps_yet=True)
    deployment = Deployment(domain=domain, data=remote_deployment)
    deployment.save()
    deployment.refresh_from_db()
    remote_deployment.no_steps_yet = False
    client = StubClient(remote_deployment)
    new_steps = deployment.get_new_steps(client=client)
    assert new_steps == [SpecialSteps.START.value]
    assert not deployment.remote.has_finished

    # start step is already seen
    deployment.refresh_from_db()
    new_steps = deployment.get_new_steps(client=client)
    assert new_steps == []


@pytest.mark.django_db
def test_deployment_in_progress(domain, remote_deployment):
    deployment = Deployment(domain=domain)
    assert not deployment.in_progress

    deployment.data = remote_deployment
    deployment.save()
    deployment.refresh_from_db()
    assert deployment.in_progress


def test_deployment_service_token_cast():
    domain = Domain(backend=Domain.Backend.CAST)
    deployment = Deployment(domain=domain)
    deployment.target = deployment.Target.DEPLOY
    assert deployment.service_token == settings.DEPLOY_CAST_SERVICE_TOKEN

    deployment.target = deployment.Target.REMOVE
    assert deployment.service_token == settings.REMOVE_CAST_SERVICE_TOKEN

    # if target is unknown, service_token is None
    deployment.target = "foo"
    assert deployment.service_token is None


def test_deployment_service_token_wordpress():
    domain = Domain(backend=Domain.Backend.WORDPRESS)
    deployment = Deployment(domain=domain)
    deployment.target = deployment.Target.DEPLOY
    assert deployment.service_token == settings.DEPLOY_WORDPRESS_SERVICE_TOKEN

    deployment.target = deployment.Target.REMOVE
    assert deployment.service_token == settings.REMOVE_WORDPRESS_SERVICE_TOKEN

    # if target is unknown, service_token is None
    deployment.target = "foo"
    assert deployment.service_token is None


def test_deployment_context_cast():
    fqdn = "foo.staging.django-cast.com"
    domain = Domain(pk=1, backend=Domain.Backend.CAST, fqdn=fqdn)
    underscored_fqdn = fqdn.replace(".", "_")
    site_id = f"cast_{underscored_fqdn}"
    user_name = f"cast_{domain.pk}"
    actual = domain.context
    expected = {
        "fqdn": fqdn,
        "site_id": site_id,
        "user_name": user_name,
        "database_name": site_id,
        "database_user": site_id,
        "database_password": actual["database_password"],
        "secret_key": actual["secret_key"],
        "port": str(10000 + domain.pk),
        "settings_file_name": site_id,
    }
    assert actual == expected


def test_deployment_context_wordpress():
    fqdn = "bar.staging.django-cast.com"
    domain = Domain(pk=1, backend=Domain.Backend.WORDPRESS, fqdn=fqdn)
    underscored_fqdn = fqdn.replace(".", "_")
    site_id = f"wp_{underscored_fqdn}"
    user_name = f"wp_{domain.pk}"
    actual = domain.context
    expected = {
        "fqdn": fqdn,
        "site_id": site_id,
        "user_name": user_name,
        "database_name": site_id,
        "database_user": site_id,
        "database_password": actual["database_password"],
        "port": str(10000 + domain.pk),
        "auth_key": actual["auth_key"],
        "secure_auth_key": actual["secure_auth_key"],
        "logged_in_key": actual["logged_in_key"],
        "nonce_key": actual["nonce_key"],
        "auth_salt": actual["auth_salt"],
        "secure_auth_salt": actual["secure_auth_salt"],
        "logged_in_salt": actual["logged_in_salt"],
        "nonce_salt": actual["nonce_salt"],
    }
    assert actual == expected


def test_deployment_context_unknown_backend():
    fqdn = "bar.staging.django-cast.com"
    domain = Domain(pk=1, backend="foo", fqdn=fqdn)
    underscored_fqdn = fqdn.replace(".", "_")
    site_id = f"wp_{underscored_fqdn}"
    user_name = f"wp_{domain.pk}"
    actual = domain.context
    expected = {
        "fqdn": fqdn,
        "site_id": site_id,
        "user_name": user_name,
        "database_name": site_id,
        "database_user": site_id,
        "database_password": actual["database_password"],
        "port": str(10000 + domain.pk),
    }
    assert actual == expected
