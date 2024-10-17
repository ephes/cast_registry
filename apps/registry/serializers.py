from django.core.serializers.json import DjangoJSONEncoder

from .fastdeploy import RemoteDeployment, Step


class RegistryJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, (RemoteDeployment, Step)):
            return o.model_dump()
        return super().default(o)
