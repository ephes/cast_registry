import pytest

from ..forms import DomainForm


@pytest.mark.django_db
def test_domain_form():
    form = DomainForm(dict(fqdn="podcast.staging.django-cast.com"))
    assert form.is_valid()
