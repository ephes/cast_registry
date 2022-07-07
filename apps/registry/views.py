from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django_htmx.http import HTMX_STOP_POLLING

from .deployment import Steps
from .forms import DomainForm
from .models import Domain


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")


@login_required
def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = DomainForm(request.POST)
        if form.is_valid():
            domain = form.save(commit=False)
            domain.owner = request.user
            domain.save()
            messages.add_message(request, messages.INFO, "Domain registered successfully")
            deployment_id = domain.start_deployment()
            success_url = reverse("deploy_progress", kwargs={"domain_id": domain.pk, "deployment_id": deployment_id})
            return HttpResponseRedirect(success_url)
    else:
        form = DomainForm(initial={"fqdn": "your-podcast.staging.django-cast.com"})
    context = {"form": form}
    return render(request, "register.html", context=context)


@login_required
@require_GET
def deploy_progress(request: HttpRequest, domain_id: int, deployment_id: int) -> HttpResponse:
    domain = get_object_or_404(Domain, pk=domain_id)
    if domain.owner != request.user:
        return HttpResponse(status=403)
    context = {"domain": domain, "deployment_id": deployment_id}
    return render(request, "deploy_progress.html", context=context)


def build_steps_html(steps: Steps) -> str:
    lines = []
    for step in steps:
        lines.append(f"<aside>{step.name}</aside>")
    return "".join(lines)


@login_required
@require_GET
def deploy_state(request: HttpRequest, domain_id: int, deployment_id: int) -> HttpResponse:
    domain = get_object_or_404(Domain, pk=domain_id)
    if domain.owner != request.user:
        return HttpResponse(status=403)
    new_steps, finished = domain.get_new_steps(request.session, deployment_id)
    html = build_steps_html(new_steps)
    if finished:
        return HttpResponse(status=HTMX_STOP_POLLING, content=html)
    else:
        return HttpResponse(status=200, content=html)


@csrf_exempt
def fade_out(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=200, content="")
