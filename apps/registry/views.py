from enum import Enum

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django_htmx.http import HTMX_STOP_POLLING

from .deployment import Client, Deployment
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
        form = DomainForm(initial={"fqdn": "yourpodcast.staging.django-cast.com"})
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


Steps = list[str]


def build_steps_html(steps: Steps) -> str:
    lines = []
    for step in steps:
        lines.append(f"<aside>{step}</aside>")
    return "".join(lines)


class Messages(Enum):
    START = "Starting deployment..."
    END = "Deployment is fertig!"


def get_deployment_state_response(deployment: Deployment, seen: Steps) -> tuple[HttpResponse, Steps]:
    # calculate all not yet seen steps
    all_steps = [Messages.START.value]
    all_steps.extend([s.name for s in deployment.steps])
    new_steps = [s for s in all_steps if s not in set(seen)]
    if deployment.finished:
        # even if deployment is finished, there might be some deployment steps
        # which were not sent to the client, so we have to include new_steps
        new_steps.append(Messages.END.value)
        return HttpResponse(status=HTMX_STOP_POLLING, content=build_steps_html(new_steps)), new_steps
    return HttpResponse(status=200, content=build_steps_html(new_steps)), new_steps


@login_required
@require_GET
def deploy_state(request: HttpRequest, domain_id: int, deployment_id: int) -> HttpResponse:
    domain = get_object_or_404(Domain, pk=domain_id)
    if domain.owner != request.user:
        return HttpResponse(status=403)
    client = Client()
    deployment = client.fetch_deployment(deployment_id)
    steps_key = f"steps_{deployment_id}"
    seen = request.session.get(steps_key, [])
    response, sent = get_deployment_state_response(deployment, seen)
    seen.extend(sent)
    request.session[steps_key] = seen
    return response


@csrf_exempt
def fade_out(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=200, content="")
