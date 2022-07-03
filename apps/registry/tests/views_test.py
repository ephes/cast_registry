import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_register_not_authenticated(client):
    url = reverse("register")
    r = client.get(url)
    assert r.status_code == 302
    assert "login" in r.url
