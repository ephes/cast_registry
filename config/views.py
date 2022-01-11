from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import OddNumberForm


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
