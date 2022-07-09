from datetime import datetime

from ..fastdeploy import RemoteDeployment, Step
from ..serializers import RegistryJSONEncoder


def test_json_serializer():
    """
    Use datetime without microseconds instead of timezone.now() because
    Django strips microseconds from timestamps it serializes to json
    because of ECMA-262 and the assertion would fail.
    """
    started = datetime(2022, 7, 22, 9)
    step = Step(name="step name", started=started)
    deployment = RemoteDeployment(id=1, service_id=1, origin="registry", user="user1", steps=[step])
    serializer = RegistryJSONEncoder()
    encoded = serializer.encode(deployment)
    decoded = RemoteDeployment.parse_raw(encoded)
    assert decoded == deployment
