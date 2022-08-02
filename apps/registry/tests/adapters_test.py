import pytest

from ..adapters import AccountAdapter, SocialAccountAdapter


@pytest.mark.parametrize(
    "allow_registration_setting, expected",
    [
        (False, False),
        (True, True),
    ],
)
def test_account_adapter_open_for_registration(settings, allow_registration_setting, expected):
    settings.ACCOUNT_ALLOW_REGISTRATION = allow_registration_setting
    assert AccountAdapter().is_open_for_signup(None) == expected


@pytest.mark.parametrize(
    "allow_registration_setting, expected",
    [
        (False, False),
        (True, True),
    ],
)
def test_social_account_adapter_open_for_registration(settings, allow_registration_setting, expected):
    settings.ACCOUNT_ALLOW_REGISTRATION = allow_registration_setting
    assert SocialAccountAdapter().is_open_for_signup(None, None) == expected
