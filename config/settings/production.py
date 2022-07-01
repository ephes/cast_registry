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
