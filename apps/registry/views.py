from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from faker import Faker

from .forms import DomainForm, OddNumberForm
from .models import Domain


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")


@login_required
@require_GET
def register(request: HttpRequest) -> HttpResponse:
    return render(request, "register.html")


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
def messages(request: HttpRequest) -> HttpResponse:
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
