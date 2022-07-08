from datetime import timedelta

from django.contrib.sessions.serializers import JSONSerializer
from django.utils import timezone

from ..deployment import Deployment, Step
from ..models import Domain


def test_session_serializer():
    step = Step(name="step name", started=timezone.now() - timedelta(minutes=2))
    deployment = Deployment(id=1, service_id=1, origin="registry", user="user1", steps=[step])
    deployment_key = Domain.get_session_key_from_deployment_id(deployment.id)
    session = {deployment_key: deployment.json(), "foo": "bar"}
    serializer = JSONSerializer()
    serialized = serializer.dumps(session)
    deserialized = serializer.loads(serialized)
    from_session = Deployment.parse_raw(deserialized.get(deployment_key))
    assert from_session == deployment
