## Installation for development

### Create a venv & activate it and install the dev requirements
```shell
     uv venv -p python3.13
     source .venv/bin/activate.fish
     uv sync
```

### Set up the database
```shell
    initdb databases/postgres
    postgres -D databases/postgres  # in a different terminal tab
    createdb cast_registry
    createuser cast_registry
    python manage.py migrate
```

### Run the tests
```shell
    pytest
```

Run tests and show coverage:
```shell
$ coverage run && coverage html && open htmlcov/index.html
```

Mypy:
```shell
$ mypy apps/registry
```

# Services

There are two preconfigured services for [fastdeploy](https://github.com/ephes/fastdeploy)
living in the `ansible` directory:
- registry
- cast
- wordpress

The registry service is used to deploy other things like cast hosting or wordpress services.
It's deployed via:
```
$ ansible-playbook register.yml
```

## Runtime and dependency maintenance

Use Python 3.11 or newer, Django 5.2 LTS (`<5.3`) and django-allauth 65.x
(`<66`). The frozen lock includes patched runtime HTTP/parser dependencies.
Username login and mandatory email verification are retained with allauth's
current settings. Python 3.10 is no longer supported: its compatible Tornado
and filelock releases still have known advisories in the developer graph.

`uv.lock` is authoritative; the old `requirements/` files are historical and
must not be used to install this application. Install with `uv sync --frozen`.
JupyterLab, Notebook, rendering/build tools and test tooling belong to the
**developer** group; production can use `uv sync --frozen --no-dev` and does not
need a notebook server. Keep developer notebook servers local and authenticated.
Deployment/controller templates are maintained separately and were not migrated.

With uv 0.13.7, audit both scopes without upgrading or resolving dependencies:

```shell
uv sync --frozen --all-groups
uv run --frozen --group audit python scripts/audit_dependencies.py
```

Push/PR CI audits Python 3.11 and 3.13. The first export includes runtime only;
the second includes every group (including the pinned pip-audit tool).
The audit first checks lock freshness offline. Exports use `--frozen`; the auditor reads PEP 751 `pylock.toml` exports with `--locked`,
checking every pin across Python/platform markers without installing packages or
resolving dependencies, reports against the advisory service, and fails on export,
lookup or vulnerability errors. There are no advisory exclusions. The audit
needs network access and caches under `.cache/pip-audit`. Refresh locks explicitly
with `uv lock --upgrade`, then repeat audits and application/notebook checks.

Notebook smoke check (does not start a server):

```shell
uv run --frozen jupyter lab --version
uv run --frozen jupyter notebook --version
uv run --frozen python -c 'import notebook, jupyterlab, jupyter_server, nbconvert, tornado'
```
