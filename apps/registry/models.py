from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .fastdeploy import AbstractClient, Client, RemoteDeployment, Steps
from .serializers import RegistryJSONEncoder


class Domain(models.Model):
    """
    Domains registered by users.
    """

    class Backend(models.TextChoices):
        CAST = "CA", _("Django-Cast")
        WORDPRESS = "WP", _("Wordpress")

    backend = models.CharField(
        max_length=2,
        choices=Backend.choices,
        default=Backend.CAST,
    )

    fqdn = models.CharField(max_length=255, unique=True, verbose_name="Enter Fully Qualified Domain Name")
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="registry")

    def __str__(self):
        return self.fqdn

    class Meta:
        ordering = ("fqdn",)

    @property
    def service_tokens(self) -> dict[str, str]:
        if self.backend == self.Backend.CAST:
            return {
                "deploy": settings.DEPLOY_CAST_SERVICE_TOKEN,
                "remove": settings.REMOVE_CAST_SERVICE_TOKEN,
            }
        return {}


class Deployment(models.Model):
    """
    Deployments have a domain for which they are deployed. They store
    a serialized version of the RemoteDeployment model fetched from fastdeploy.
    """

    class Target(models.TextChoices):
        DEPLOY = "DP", _("Deploy")
        REMOVE = "RM", _("Remove")

    target = models.CharField(
        max_length=2,
        choices=Target.choices,
        default=Target.DEPLOY,
    )

    data = models.JSONField(encoder=RegistryJSONEncoder, null=True)
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE)

    @property
    def remote(self):
        if self.data is None:
            return None
        return RemoteDeployment.parse_obj(self.data)

    def start(self, client: AbstractClient = Client()):
        self.data = client.start_deployment(self)

    def get_new_steps(self, client: AbstractClient = Client()) -> Steps:
        """
        If the deployment has finished, it's possible to return early that
        there are no new steps.

        If it hasn't finished yet, fetch a new version of the deployment
        via client and use it to calculate the list of unseen steps.
        """
        if self.remote.has_finished:
            return []

        deployment = client.fetch_deployment(self)
        new_steps = deployment.get_new_steps(self.remote)
        self.data = deployment  # deployment is the new remote
        self.save()
        return new_steps

    @property
    def has_finished(self):
        if self.remote is None:
            return False
        return self.remote.has_finished

    @property
    def in_progress(self):
        if self.remote is None:
            return False
        return not self.has_finished

    @property
    def service_token(self) -> str | None:
        service_tokens = self.domain.service_tokens
        if self.target == self.Target.DEPLOY:
            return service_tokens["deploy"]
        elif self.target == self.Target.REMOVE:
            return service_tokens["remove"]
