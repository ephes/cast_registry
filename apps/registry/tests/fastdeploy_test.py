from datetime import timedelta

import pytest
from django.utils import timezone

from ..fastdeploy import RemoteDeployment, SpecialSteps, Step

NEW = Step(id=2, name="new")
NOT_NEW = Step(id=2, name="not new")


@pytest.mark.parametrize(
    "deployment, seen, expected",
    [
        (
            RemoteDeployment(),
            RemoteDeployment(no_steps_yet=True),
            [SpecialSteps.START.value],
        ),  # no deployment seen before
        (
            RemoteDeployment(finished=timezone.now()),
            RemoteDeployment(),
            [SpecialSteps.END.value],
        ),  # only finished step
        (RemoteDeployment(steps=[NEW]), RemoteDeployment(), [NEW]),  # new step
        (RemoteDeployment(steps=[NOT_NEW]), RemoteDeployment(steps=[NOT_NEW]), []),  # no new step -> []
    ],
)
def test_get_new_step(deployment, seen, expected):
    assert deployment.get_new_steps(seen) == expected


def test_sort_steps():
    start_none = Step(name="start_none", started=None)
    start_now = Step(name="start_none", started=timezone.now())
    assert [start_none, start_now] == sorted([start_none, start_now])
    assert [start_none, start_now] == sorted([start_now, start_none])

    start_later = Step(name="start_later", started=timezone.now() + timedelta(minutes=2))
    assert [start_now, start_later] == sorted([start_later, start_now])
    assert [start_none, start_none] == sorted([start_none, start_none])
