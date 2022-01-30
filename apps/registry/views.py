from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
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
    html = f"<p>{current_step}</p>"
    if deployment.finished is None:
        return HttpResponse(status=200, content=html)
    else:
        return HttpResponse(status=HTMX_STOP_POLLING)


@csrf_exempt
def fade_out(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=200, content="")


deployment_in_progress = False


@require_POST
def create_domain(request: HttpRequest) -> HttpResponse:
    form = DomainForm(request.POST)
    if form.is_valid():
        domain = form.save(commit=False)
        user = get_user_model().objects.get(username="jochen")
        domain.owner = user
        domain.save()
        global deployment_in_progress
        deployment_in_progress = True
        return redirect("list_domains")
    else:
        return redirect("list_domains")


state = 0


@require_GET
def list_domains(request: HttpRequest) -> HttpResponse:
    print("get data: ", request.GET)
    global state
    state = 0
    domains = Domain.objects.all()
    form = DomainForm()
    return render(
        request,
        "registry/list-domains.html",
        {"domains": domains, "form": form, "show_progress": deployment_in_progress},
    )


@require_GET
def show_messages(request: HttpRequest) -> HttpResponse:
    global state
    body = f"""
    hello world {state}
    """
    code = 200
    if state <= 10:
        content = body
    else:
        content = "stop"
        code = 286
    state += 1
    print("content: ", content)
    return HttpResponse(status=code, content=content)
