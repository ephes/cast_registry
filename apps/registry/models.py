from typing import MutableMapping

from django.conf import settings
from django.db import models

from .fastdeploy import AbstractClient, Client, Finished, RemoteDeployment, Steps


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

    @staticmethod
    def get_session_key_from_deployment_id(deployment_id: int) -> str:
        return f"deployment_{deployment_id}"

    def start_deployment(self, session: MutableMapping, client: AbstractClient = Client()) -> int:
        """Start a deployment for this domain"""
        deployment = client.start_deployment(self)
        assert deployment.id is not None
        key = self.get_session_key_from_deployment_id(deployment.id)
        session[key] = deployment.json()
        return deployment.id

    def get_new_steps(
        self, session: MutableMapping, deployment_id: int, client: AbstractClient = Client()
    ) -> tuple[Steps, Finished]:
        """
        Fetch already seen deployment for this deployment_id from session
        and use it to find the new steps in the deployment fetched from
        http client. We have to double encode the deployment objects as a
        workaround, because Django's standard session serializer cannot
        encode datetime objects like deployment.finished. Therefore, pydantic
        deployment.json() is used. Not pretty, but it works.
        """
        deployment_key = self.get_session_key_from_deployment_id(deployment_id)
        seen_deployment = RemoteDeployment.parse_raw(session[deployment_key])
        deployment = client.fetch_deployment(deployment_id)
        new_steps = deployment.get_new_steps(seen_deployment)
        if deployment.has_finished:
            del session[deployment_key]
        else:
            session[deployment_key] = deployment.json()
        return new_steps, deployment.has_finished
