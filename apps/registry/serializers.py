from django.core.serializers.json import DjangoJSONEncoder

from .fastdeploy import RemoteDeployment


class RegistryJSONEncoder(DjangoJSONEncoder):
    def default(self, o):
        if isinstance(o, RemoteDeployment):
            return o.dict()
        return super().default(o)
