from typing import MutableMapping

from django.conf import settings
from django.db import models

from .deployment import AbstractClient, Client, Deployment, Finished, Steps


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

    def start_deployment(self) -> int:
        """Start a deployment for this domain"""
        client = Client()
        return client.start_deployment(self)

    @staticmethod
    def get_new_steps(
        session: MutableMapping, deployment_id: int, client: AbstractClient = Client()
    ) -> tuple[Steps, Finished]:
        """
        Fetch already seen deployment for this deployment_id from session
        and use it to find the new steps in the deployment fetched from
        http client. We have to double encode the deployment objects as a
        workaround, because Django's standard session serializer cannot
        encode datetime objects like deployment.finished. Therefore, pydantic
        deployment.json() is used. Not pretty, but it works.
        """
        deployment_key = f"deployment_{deployment_id}"
        seen_json = seen_deployment = session.get(deployment_key)
        if seen_json is not None:
            seen_deployment = Deployment.parse_raw(seen_json)
        deployment = client.fetch_deployment(deployment_id)
        new_steps = deployment.get_new_steps(seen_deployment)
        if deployment.has_finished:
            del session[deployment_key]
        else:
            session[deployment_key] = deployment.json()
        return new_steps, deployment.has_finished
