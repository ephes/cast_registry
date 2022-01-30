from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django_htmx.http import HTMX_STOP_POLLING

from .deployment import Client
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
            client = Client()
            deployment_id = client.start_deployment()
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


@login_required
@require_GET
def deploy_state(request: HttpRequest, domain_id: int, deployment_id: int) -> HttpResponse:
    domain = get_object_or_404(Domain, pk=domain_id)
    if domain.owner != request.user:
        return HttpResponse(status=403)
    client = Client()
    deployment = client.fetch_deployment(deployment_id)
    if len(deployment.steps) > 0:
        current_step = deployment.steps[0].name
    else:
        current_step = "Starting deployment..."
    html = f"<aside>{current_step}</aside>"
    if deployment.finished is None:
        return HttpResponse(status=200, content=html)
    else:
        html = "<aside>Deployment is fertig!</aside>"
        return HttpResponse(status=HTMX_STOP_POLLING, content=html)


@csrf_exempt
def fade_out(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=200, content="")
