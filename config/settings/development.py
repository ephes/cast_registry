"""
Django settings for cast_registry project in development mode

This fill will be automatically used when using `manage.py`.
See `base.py` for basic settings.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""


from .base import *  # noqa

DEBUG = True

# for development, we don't need password validation
AUTH_PASSWORD_VALIDATORS = []
