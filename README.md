## Isolated development and validation

Use uv 0.13.7 and Python 3.11+ (CI tests 3.11 and 3.13). No `.env`, service
tokens, production database or deployment controller is needed for validation.

```shell
uv sync --frozen --python 3.13
export DJANGO_SETTINGS_MODULE=config.settings.test
export DATABASE_URL=postgres://registry_test@localhost:55432/registry_test
mkdir -p databases
initdb databases/postgres --auth=trust --username=registry_test --encoding=UTF8
pg_ctl -D databases/postgres -l databases/postgres.log -o '-p 55432' start
createdb -h localhost -p 55432 -U registry_test registry_test
uv run --frozen python manage.py check
uv run --frozen python manage.py makemigrations --check --dry-run
uv run --frozen python manage.py migrate --noinput
uv run --frozen python manage.py migrate --check
uv run --frozen coverage run
uv run --frozen coverage report --fail-under=100
uv run --frozen mypy apps/registry
pg_ctl -D databases/postgres stop
```

Choose an unused local port. Use only a new,
disposable cluster: tests create/drop their own test database. When PostgreSQL
is unavailable, `DATABASE_URL=sqlite:///:memory: uv run --frozen pytest` provides
a local application check; it does not replace the PostgreSQL CI gate.

The test settings use a dummy key, in-memory email and the fake deployment
client. An autouse fixture blocks real HTTPX transports, including accidental
production deployment calls; production-client tests inject fake HTTP clients.
All rows and notebook smoke content are synthetic. Mypy also loads test settings.

Run the configured formatters/linters without modifying files (migrations retain
the existing pre-commit exclusion):

```shell
uv run --frozen black --check --extend-exclude migrations apps config scripts manage.py commands.py
uv run --frozen isort --check-only --skip-glob '*/migrations/*' apps config scripts manage.py commands.py
uv run --frozen flake8 --extend-exclude migrations apps config scripts manage.py commands.py
uv run --frozen djhtml --check -t 2 templates
```

Push/PR CI runs these checks, mypy, fresh/missing migration checks, tests with
100% registry coverage, and notebook CLI/rendering smoke on disposable PostgreSQL
17 services. No deployment commands run in CI. The small template indentation
cleanup only brings existing templates into sync with the configured formatter.
There is no existing changelog; maintenance and behavior changes are recorded here.

## Registry view contracts

Remote deployment step names are plain text. Poll responses escape HTML, script,
ampersand and quote characters inside the existing `<aside>` markup; a finished
deployment still returns status 286 to stop polling. Owner authorization is unchanged.

Domain and deployment history pages use scalar `page` query values (the last
value wins when repeated). Missing or nonnumeric values select page 1;
out-of-range values select the last page, following Django Paginator's normal
fallback. Domain lists remain owner-filtered and deployment histories remain
restricted to the authorized domain.

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
