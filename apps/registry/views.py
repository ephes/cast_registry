from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django_htmx.http import HTMX_STOP_POLLING

from .fastdeploy import Steps
from .forms import DeploymentForm, DomainForm
from .models import Deployment, Domain


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
            print("---------------------------")
            print("domain saved..")
            messages.add_message(request, messages.INFO, "Domain registered successfully")
            # deployment_id = domain.start_deployment(request.session)
            # success_url = reverse("deploy_progress", kwargs={"domain_id": domain.pk, "deployment_id": deployment_id})
            success_url = reverse("domains")
            print("redirect to: ", success_url)
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
    try:
        new_steps, finished = domain.get_new_steps(request.session, deployment_id)
    except KeyError:
        # deployment with deployment_id not in session
        return HttpResponse(status=404)
    html = build_steps_html(new_steps)
    if finished:
        return HttpResponse(status=HTMX_STOP_POLLING, content=html)
    else:
        return HttpResponse(status=200, content=html)


@csrf_exempt
def fade_out(request: HttpRequest) -> HttpResponse:
    return HttpResponse(status=200, content="")


def register_domain(request: HttpRequest):
    form = DomainForm(request.POST)
    if form.is_valid():
        domain = form.save(commit=False)
        domain.owner = request.user
        domain.save()
        messages.add_message(request, messages.INFO, "Domain registered successfully")
        success_url = reverse("domains")
        return HttpResponseRedirect(success_url)
    else:
        return


def render_partial_or_full(request: HttpRequest, template_name: str, context: dict):
    if request.htmx:
        base_template = "_partial.html"
    else:
        base_template = "_base.html"
    context["base_template"] = base_template
    return render(request, template_name, context)


@login_required
def domains(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = DomainForm(request.POST)
        if form.is_valid():
            domain = form.save(commit=False)
            domain.owner = request.user
            domain.save()
            messages.add_message(request, messages.INFO, "Domain registered successfully")
            success_url = reverse("domains")
            return HttpResponseRedirect(success_url)
    else:
        form = DomainForm(initial={"fqdn": "your-podcast.staging.django-cast.com"})

    registered_domains = Domain.objects.filter(owner=request.user).order_by("pk")
    page_num = request.GET.get("page", "1")
    page = Paginator(object_list=registered_domains, per_page=2).get_page(page_num)
    context = {"form": form, "page": page}
    return render_partial_or_full(request, "domains.html", context)


@login_required
def domain_deployments(request: HttpRequest, domain_id: int) -> HttpResponse:
    domain = get_object_or_404(Domain, pk=domain_id)
    if domain.owner != request.user:
        return HttpResponse(status=403)
    if request.method == "POST":
        form = DeploymentForm(request.POST, initial={"domain": domain})
        if form.is_valid():
            deployment = form.save(commit=False)
            deployment.save()
            messages.add_message(request, messages.INFO, "Deployment created successfully")
            success_url = reverse("domain_deployments", kwargs={"domain_id": domain.pk})
            return HttpResponseRedirect(success_url)
    else:
        form = DeploymentForm(initial={"target": Deployment.Target.DEPLOY.value, "domain": domain})

    deployments = Deployment.objects.filter(domain=domain).order_by("pk")
    page_num = request.GET.get("page", "1")
    page = Paginator(object_list=deployments, per_page=2).get_page(page_num)
    context = {
        "form": form,
        "domain": domain,
        "page": page,
    }
    return render_partial_or_full(request, "domain_deployments.html", context)
