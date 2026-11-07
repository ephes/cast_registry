// Admission conflicts carry a rendered form with actionable reconciliation choices.
document.addEventListener("htmx:beforeSwap", function (event) {
    if (event.detail.xhr.status === 409 && event.detail.target.id === "main" && event.detail.requestConfig.verb === "post") {
        event.detail.shouldSwap = true;
        event.detail.isError = false;
    }
});
// Intentional form submissions move focus; pagination leaves focus alone.
document.addEventListener("htmx:afterSwap", function (event) {
    if (event.detail.target.id !== "main" || event.detail.requestConfig.verb !== "post") return;
    const main = document.getElementById("main");
    const destination = main.querySelector('[aria-invalid="true"]') || main.querySelector("#form-feedback");
    if (destination) destination.focus();
});
document.addEventListener("htmx:beforeRequest", function (event) {
    const form = event.detail.elt;
    if (!form.matches("[data-registry-form]")) return;
    form.setAttribute("aria-busy", "true");
    form.querySelector("[data-request-error]").hidden = true;
});
document.addEventListener("htmx:afterRequest", function (event) {
    const form = event.detail.elt;
    if (!form.matches("[data-registry-form]")) return;
    form.removeAttribute("aria-busy");
    if (!event.detail.successful) form.querySelector("[data-request-error]").hidden = false;
});
