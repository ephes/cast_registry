from ..fastdeploy import RemoteDeployment
from ..serializers import RegistryJSONEncoder


def test_json_serializer(remote_deployment):
    serializer = RegistryJSONEncoder()
    encoded = serializer.encode(remote_deployment)
    decoded = RemoteDeployment.parse_raw(encoded)
    assert decoded == remote_deployment
