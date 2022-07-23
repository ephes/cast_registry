"""
Django settings for cast_registry project in production mode

This fill will be automatically used when using a dedicated application server.
See `base.py` for basic settings.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""


from .base import *  # noqa
from .base import env

DEBUG = False

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = ""
SECRET_KEY = env("DJANGO_SECRET_KEY")

# remember to set this to your expected hostnames
ALLOWED_HOST = env("ALLOWED_HOST")
ALLOWED_HOSTS = [ALLOWED_HOST]

# static files
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Custom Admin URL, use {% url 'admin:index' %}
ADMIN_URL = env("DJANGO_ADMIN_URL")

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#default-from-email
DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL", default="Cast Registry <noreply@email.registry.staging.django-cast.com>"
)
# https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
# https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = env("DJANGO_EMAIL_SUBJECT_PREFIX", default="[Cast Registry]")

# Anymail (Mailgun)
# ------------------------------------------------------------------------------
# https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
INSTALLED_APPS += ["anymail"]  # noqa F405
EMAIL_BACKEND = "anymail.backends.mailgun.EmailBackend"
# https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
ANYMAIL = {"MAILGUN_API_KEY": env("MAILGUN_API_KEY"), "MAILGUN_SENDER_DOMAIN": env("MAILGUN_DOMAIN")}
