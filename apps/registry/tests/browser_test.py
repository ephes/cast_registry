"""Real Chromium, shipped HTMX and production views; all HTTP stays synthetic."""

from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.conf import settings
from django.db import connections
from django.urls import reverse
from playwright.sync_api import expect, sync_playwright

from ..models import Deployment, Domain


@pytest.fixture
def browser_page(client, user, monkeypatch):
    # Playwright callbacks use a separate Django connection; fixtures must be committed.
    monkeypatch.setenv("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
    client.force_login(user)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        def respond_impl(route):
            request = route.request
            url = urlsplit(request.url)
            if url.path.startswith("/static/"):
                path = Path(settings.BASE_DIR) / "static" / url.path.removeprefix("/static/")
                if path.is_file():
                    route.fulfill(path=str(path))
                else:
                    route.fulfill(status=404)
                return
            headers = {k: v for k, v in request.headers.items() if k.startswith("hx-")}
            if request.method == "POST":
                data = {k: v[-1] for k, v in parse_qs(request.post_data or "").items()}
                response = client.post(url.path, data, headers=headers, follow=True)
            else:
                response = client.get(url.path + ("?" + url.query if url.query else ""), headers=headers)
            route.fulfill(status=response.status_code, body=response.content, content_type="text/html")

        def respond(route):
            try:
                respond_impl(route)
            finally:
                connections.close_all()

        page.route("**/*", respond)
        yield page
        browser.close()
        connections.close_all()


@pytest.mark.django_db(transaction=True)
def test_registration_swaps_feedback_focus_and_pagination(browser_page, user, client):
    page = browser_page
    for i in range(4):
        Domain.objects.create(owner=user, fqdn=f"fixture-{i}.example.com")
    page.goto("http://testserver" + reverse("domains"))
    for i in range(2):
        page.locator("[name=fqdn]").fill("fixture-0.example.com")
        page.get_by_role("button", name="Submit").click()
        expect(page.locator("[name=fqdn]")).to_be_focused()
        expect(page.get_by_role("alert")).to_have_text("Please correct the errors below.")
        expect(page.locator("main")).to_have_count(1)
        page.locator("[name=fqdn]").fill(f"new-{i}.example.com")
        page.get_by_role("button", name="Submit").click()
        expect(page.get_by_role("status").filter(has_text="Domain registered successfully")).to_be_focused()
        expect(page.get_by_text("Domain registered successfully", exact=True)).to_have_count(1)
        expect(page.locator("#main")).to_have_count(1)
        page.get_by_role("link", name="2", exact=True).click()
        expect(page.locator('nav a[hx-get="?page=1"]').first).to_be_visible()
        expect(page.locator("#main")).to_have_count(1)
        assert page.locator("#form-feedback").count() == 0
    page.reload()
    expect(page.get_by_text("Domain registered successfully", exact=True)).to_have_count(0)
    response = client.post(reverse("domains"), {"fqdn": "ordinary.example.com", "backend": "CA"}, follow=True)
    assert response.content.count(b"Domain registered successfully") == 1
    assert b"<!doctype html>" in response.content


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("outcome", ["success", "refused", "transport"])
def test_deployment_single_pending_submission(browser_page, domain, outcome):
    page = browser_page
    url = reverse("domain_deployments", args=[domain.pk])
    page.goto("http://testserver" + url)
    pending = []
    page.route("**" + url, lambda route: pending.append(route) if route.request.method == "POST" else route.fallback())
    page.get_by_role("button", name="Submit").click()
    expect(page.get_by_role("button", name="Submit")).to_be_disabled()
    expect(page.locator("form")).to_have_attribute("aria-busy", "true")
    page.locator("form").evaluate("(form) => { for (let i=0;i<4;i++) form.requestSubmit(); }")
    page.locator("[name=target]").press("Enter")
    assert len(pending) == 1
    with patch("apps.registry.fastdeploy.TestClient.start_deployment") as start:
        if outcome == "transport":
            pending.pop().abort("failed")
        else:
            from ..fastdeploy import RemoteDeployment

            start.return_value = RemoteDeployment(id=1, no_steps_yet=True)
            if outcome == "refused":
                start.side_effect = RuntimeError("synthetic refusal")
            pending.pop().fallback()
        expect(page.get_by_role("button", name="Submit")).to_be_enabled()
        expect(page.locator("form")).not_to_have_attribute("aria-busy", "true")
        assert start.call_count == (0 if outcome == "transport" else 1)
    if outcome == "transport":
        expect(page.get_by_role("alert")).to_contain_text("Request unavailable")
    page.get_by_role("button", name="Submit").click()
    expect(page.get_by_role("button", name="Submit")).to_be_disabled()
    assert len(pending) == 1
    pending.pop().abort("failed")
    expect(page.get_by_role("button", name="Submit")).to_be_enabled()
    assert Deployment.objects.filter(domain=domain).count() == (0 if outcome == "transport" else 1)


@pytest.mark.django_db(transaction=True)
def test_pagination_history_cache_miss_keeps_document(browser_page, user):
    page = browser_page
    for i in range(4):
        Domain.objects.create(owner=user, fqdn=f"history-{i}.example.com")
    page.goto("http://testserver" + reverse("domains"))
    page.get_by_role("link", name="2", exact=True).click()
    page.wait_for_url("**?page=2")
    page.evaluate("localStorage.removeItem('htmx-history-cache')")
    page.go_back()
    expect(page.get_by_text("history-0.example.com", exact=True)).to_be_visible()
    expect(page.locator("body > header")).to_have_count(1)
    expect(page.locator("body > footer")).to_have_count(1)
    expect(page.locator("main#main")).to_have_count(1)


@pytest.mark.django_db(transaction=True)
def test_progress_snapshot_error_retry_and_terminal_swap(browser_page, deployment):
    import httpx
    from django.utils import timezone

    from ..fastdeploy import RemoteDeployment, Step

    deployment.data = RemoteDeployment(id=1, no_steps_yet=True)
    deployment.save()
    first = RemoteDeployment(id=1, steps=[Step(id=1, name="download")])
    final = RemoteDeployment(id=1, steps=[Step(id=2, name="install")], finished=timezone.now())
    page = browser_page
    with patch(
        "apps.registry.fastdeploy.TestClient.fetch_deployment",
        side_effect=[first, httpx.ConnectError("private controller detail"), final],
    ) as fetch:
        page.goto("http://testserver" + reverse("domain_deployments", args=[deployment.domain_id]))
        expect(page.locator("[data-progress-steps]")).to_contain_text("download")
        expect(page.get_by_role("alert")).to_have_text("Progress unavailable. Displayed steps may be stale.")
        expect(page.locator("[data-progress-steps]").locator("aside", has_text="download")).to_have_count(1)
        expect(page.get_by_text("Last successful refresh:", exact=False)).to_be_visible()
        assert page.get_by_text("private controller detail").count() == 0
        page.get_by_role("button", name="Refresh progress").click()
        expect(page.get_by_role("status").filter(has_text="Deployment finished.")).to_be_visible()
        expect(page.locator("[data-progress-steps]").locator("aside", has_text="download")).to_have_count(1)
        expect(page.locator("[data-progress-steps]").locator("aside", has_text="install")).to_have_count(1)
        expect(page.locator("[data-progress-steps]").locator("aside", has_text="Deployment is done!")).to_have_count(1)
        expect(page.locator(f"#progress-{deployment.pk}")).to_have_count(1)
        assert page.locator('[hx-trigger="every 1s"]').count() == 0
        assert fetch.call_count == 3
