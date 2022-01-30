from django.conf import settings
from django.db import models


class Domain(models.Model):
    """
    Domains registered by users.
    """

    fqdn = models.CharField(max_length=255, unique=True, verbose_name="Enter Fully Qualified Domain Name")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registry")

    def __str__(self):
        return self.fqdn

    class Meta:
        ordering = ("fqdn",)
