## Isolated development and validation

Use uv 0.13.7 and Python 3.11+ (CI tests 3.11 and 3.13). No `.env`, service
tokens, production database or deployment controller is needed for validation.

```shell
uv sync --frozen --python 3.13
uv run --frozen playwright install chromium
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

## Form interaction

Registration, deployment and pagination replace the single main wrapper using
vendored HTMX 1.9.12. Ordinary forms retain POST/redirect/GET without JavaScript.
Feedback is consumed once inside the replaced region. Intentional submissions
focus the first invalid field or confirmation; pagination does not move focus.
Pending forms disable their submit button, announce submission and drop repeated
submissions until the request ends. Transport errors restore the form and advise
checking the result before another attempt. Server admission also serializes deployment and removal across clients (see below). Chromium regressions run in the normal pytest
suite against synthetic Django responses and the shipped scripts, without a
controller or live application server.

## Deployment progress and launch outcomes

Each progress response replaces a cumulative, escaped snapshot, so independent
viewers see every recorded step once, including the final step. PostgreSQL row
locks serialize refresh/publication for a deployment; an older remote snapshot
cannot remove recorded steps or reopen a terminal deployment. Owner checks apply
to every poll. The last successful refresh time remains visible. HTTP/transport
and malformed-response failures preserve the snapshot, announce that it may be stale and pause automatic
polling; **Refresh progress** retries explicitly and resumes polling on recovery.
Terminal responses still use HTMX status 286 and contain no automatic poller.

A failed or uncertain start is saved in history with a safe explanation and no
running poller. No raw controller exception is stored or shown. Check the actual
service before choosing **Prepare a new attempt**, then deliberately submit the
prefilled target and explicitly select the checked unconfirmed attempt in the form. This creates a new history row and never replays or overwrites
the original attempt; a timeout can mean the remote service did start.

Failure logs contain only the local deployment ID and error class; remote exception
text is neither persisted in history nor logged. The cumulative steps remain
readable text; only stale/error feedback uses an alert, avoiding announcements
of the entire history and timestamp on every poll.

## Domain safety and deployment admission

Registered names must be lowercase ASCII DNS names without a trailing dot,
up to 253 characters, and pass Django's public domain-name validator, for example `podcast.example.test` or a punycode hostname.
Paths, URLs, userinfo, ports, whitespace, Unicode, IP addresses, shell syntax and
alternate case/trailing-dot spellings are rejected.
Names and derived identifiers are not normalized or silently rewritten. Invalid
legacy rows cannot produce deployment context or be submitted for deployment;
correct them deliberately before use.

Deployment and removal share a domain-row admission lock. A history row is
committed before the controller call, so pending, running and unconfirmed starts
block other clients with HTTP 409. Finished attempts do not block. After checking
the actual service, explicitly select each unconfirmed attempt that is safe to
replace; this acknowledgement releases only those attempts and is recorded without
changing their failure history. Replaying an acknowledgement cannot release a
later attempt. A process crash before confirmation leaves a blocking pending row:
an operator must reconcile its real service state before using `manage.py shell`
to mark that specific row as `start_failed` for explicit acknowledgement. This is
an administrative database operation; there is no automatic crash recovery action. Never automatically retry it.

## Credentialed controller requests

Set `DEPLOY_BASE_URL` explicitly to an absolute HTTPS URL, optionally with an API
path prefix, such as `https://controller.example.test/api/`. Relative URLs,
userinfo, queries, fragments, invalid ports and whitespace/control characters are
configuration errors, rejected before sending service credentials or generated
application secrets. Errors never include the configured URL. TLS verification
remains enabled and redirects are not followed. For local development only, set
`DEPLOY_ALLOW_LOOPBACK_HTTP=true` to allow HTTP to `localhost`, IPv4 loopback or
`::1`; remote HTTP remains forbidden. There is no default controller endpoint.

Both start and progress responses stream with a **1 MiB raw-body budget** and a
**10 second whole-exchange deadline**, including connection, headers and drip-fed
body transfer. HTTPX also retains per-operation timeouts. Controllers must return
uncompressed JSON: requests advertise `Accept-Encoding: identity`, and encoded
responses are rejected before decoding to prevent decompression amplification.
HTTP status and response schema checks remain in place. Byte, time, encoding and
JSON-decoding failures close the response and use the existing safe error path:
starts remain unconfirmed, and polling preserves the last snapshot, releases its
row lock and pauses automatic refresh. No raw response body is logged or stored
on failure. Production's synchronous adapter uses asyncio cancellation and
HTTPX's async streaming client to enforce the whole-exchange deadline. Each
request closes its event loop without joining a cancelled native DNS worker,
so a stalled system resolver cannot retain the request or database row lock.
The native resolver itself may finish later; cancellation prevents its result
from continuing the controller request.
