import pytest

from ..forms import DeploymentForm, DomainForm


@pytest.mark.django_db
def test_domain_form():
    form = DomainForm(dict(fqdn="podcast.staging.django-cast.com"))
    assert form.is_valid()


def test_deployment_form_invalid():
    form = DeploymentForm(dict(foo="bar"))
    assert form.errors["domain"] == ["This field is required."]
    assert form.errors["target"] == ["This field is required."]


@pytest.mark.django_db
def test_deployment_form_valid(domain):
    form = DeploymentForm(dict(target="DP"), initial={"domain": domain})
    assert form.is_valid()
