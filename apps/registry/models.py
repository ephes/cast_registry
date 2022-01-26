from django.db import models

from django.conf import settings


class Domain(models.Model):
    """
    Domains registered by users.
    """
    fqdn = models.CharField(max_length=255, unique=True, verbose_name="Fully Qualified Domain Name")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='registry')

    def __str__(self):
        return self.fqdn

    class Meta:
        ordering = ('fqdn',)