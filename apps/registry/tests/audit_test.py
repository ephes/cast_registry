import subprocess

import pytest

from scripts.audit_dependencies import main


@pytest.mark.parametrize("failure_at", [1, 2, 3, 4, 5])
def test_audit_or_export_failure_is_blocking(monkeypatch, failure_at):
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["check"] is True
        if len(calls) == failure_at:
            raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(subprocess, "run", run)
    with pytest.raises(subprocess.CalledProcessError):
        main()
    assert len(calls) == failure_at
