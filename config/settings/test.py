"""
Django settings for cast_registry project in test mode

Make sure to override `DJANGO_SETTINGS_MODULE` environment variable to use this file.
See `base.py` for basic settings.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

from .base import *  # noqa

DEPLOY_CLIENT = "test"
