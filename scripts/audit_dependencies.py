"""Audit both frozen lockfile scopes without resolving or upgrading packages."""

import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    subprocess.run(["uv", "lock", "--check", "--offline"], check=True)
    with tempfile.TemporaryDirectory() as directory:
        for scope, groups in (("runtime", ["--no-dev"]), ("all-groups", ["--all-groups"])):
            scope_dir = Path(directory) / scope
            scope_dir.mkdir()
            lockfile = scope_dir / "pylock.toml"
            subprocess.run(
                [
                    "uv",
                    "export",
                    "--frozen",
                    "--no-emit-project",
                    "--format",
                    "pylock.toml",
                    *groups,
                    "--output-file",
                    str(lockfile),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            print(f"Auditing {scope}", flush=True)
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip_audit",
                    "--strict",
                    "--locked",
                    "--cache-dir",
                    ".cache/pip-audit",
                    str(scope_dir),
                ],
                check=True,
            )


if __name__ == "__main__":
    main()
