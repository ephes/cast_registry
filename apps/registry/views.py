from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from faker import Faker

from .forms import DomainForm, OddNumberForm
from .models import Domain


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    return render(request, "home.html")


@require_GET
def csrf_demo(request: HttpRequest) -> HttpResponse:
    return render(request, "csrf-demo.html")


@require_http_methods(("POST",))
def csrf_demo_checker(request: HttpRequest) -> HttpResponse:
    form = OddNumberForm(request.POST)
    if form.is_valid():
        number = form.cleaned_data["number"]
        number_is_odd = number % 2 == 1
    else:
        number_is_odd = False
    return render(
        request,
        "csrf-demo-checker.html",
        {"form": form, "number_is_odd": number_is_odd},
    )


@dataclass
class Person:
    id: int
    name: str


faker = Faker()
people = [Person(id=i, name=faker.name()) for i in range(1, 235)]


@require_GET
def partial_rendering(request: HttpRequest) -> HttpResponse:
    # Standard Django pagination
    page_num = request.GET.get("page", "1")
    page = Paginator(object_list=people, per_page=10).get_page(page_num)

    # The htmx magic - use a different, minimal base template for htmx
    # requests, allowing us to skip rendering the unchanging parts of the
    # template.
    if request.htmx:
        base_template = "_partial.html"
    else:
        base_template = "_base.html"

    return render(
        request,
        "partial-rendering.html",
        {
            "base_template": base_template,
            "page": page,
        },
    )


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
