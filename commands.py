import contextlib
import os
import platform
import subprocess
import sys
from pathlib import Path


def bootstrap():
    """
    Called when first non-standard lib import fails.
    """
    if not (Path.cwd() / ".venv").exists():
        print("No .venv found, creating one using uv...")
        subprocess.run(["uv", "venv", ".venv"], check=True)
        print("Please activate the virtual environment and run the script again.")
        sys.exit(1)

    print("Sync requirements via uv...")
    subprocess.run(["uv", "sync"], check=True)


try:
    import typer
except ImportError:
    bootstrap()
    import typer

from rich import print  # noqa

cli = typer.Typer()


def get_pythonpath():
    """Add project root and model directory to string"""
    project_root = str(Path(__file__).parent.resolve())
    model_root = str(Path(__file__).parent / "model")
    return f"{project_root}:{model_root}"


def env_with_pythonpath():
    """Get en environment dict with includes PYTHONPATH"""
    env = os.environ.copy()
    env["PYTHONPATH"] = get_pythonpath()
    return env


@cli.command()
def mypy():
    """Run Mypy (configured in pyproject.toml)"""
    subprocess.call(["mypy", "."])


@cli.command()
def test():
    subprocess.call(["python", "-m", "pytest"], env=env_with_pythonpath())


@cli.command()
def coverage():
    """
    Run and show coverage.
    """
    subprocess.call(["coverage", "run", "-m", "pytest"], env=env_with_pythonpath())
    subprocess.call(["coverage", "html"])
    if platform.system() == "Darwin":
        subprocess.call(["open", "htmlcov/index.html"])
    elif platform.system() == "Linux" and "Microsoft" in platform.release():  # on WSL
        subprocess.call(["explorer.exe", r"htmlcov\index.html"])


@cli.command()
def update():
    """
    update the backend requirements using uv.
    """
    subprocess.call(["uv", "lock", "--upgrade"])


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd().absolute()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev_cwd)


def deploy(environment):
    """
    Use ansible-playbook to deploy the site to the staging server.
    """
    deploy_root = Path(__file__).parent / "ansible/registry"
    with working_directory(deploy_root):
        subprocess.call(["ansible-playbook", "deploy.yml", "--limit", environment])


@cli.command()
def deploy_staging():
    """Deploy to the staging environment."""
    deploy("staging")


@cli.command()
def deploy_production():
    """Deploy to the production environment."""
    deploy("production")


if __name__ == "__main__":
    cli()
