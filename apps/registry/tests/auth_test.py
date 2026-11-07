import pytest
from allauth.account.models import EmailAddress
from django.core import mail
from django.urls import reverse


@pytest.mark.django_db
def test_signup_requires_email_and_sends_verification(client, django_user_model):
    url = reverse("account_signup")
    data = {"username": "synthetic", "password1": "synthetic-password-293!", "password2": "synthetic-password-293!"}
    response = client.post(url, data)
    assert response.status_code == 200
    assert "email" in response.context["form"].errors
    assert not django_user_model.objects.filter(username="synthetic").exists()
    response = client.post(url, data | {"email": "synthetic@example.com"})
    assert response.status_code == 302
    address = EmailAddress.objects.get(user__username="synthetic")
    assert not address.verified
    assert len(mail.outbox) == 1


@pytest.mark.django_db
def test_username_login_requires_verified_email(client, user):
    url = reverse("account_login")
    data = {"login": user.username, "password": user._password}
    address = EmailAddress.objects.create(user=user, email="owner@example.com", primary=True, verified=False)
    response = client.post(url, data)
    assert response.status_code == 302
    assert "_auth_user_id" not in client.session
    address.verified = True
    address.save()
    response = client.post(url, data)
    assert response.status_code == 302
    assert client.session["_auth_user_id"] == str(user.pk)
