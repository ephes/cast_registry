from django import forms

from .models import Deployment, Domain
from .validators import validate_deployment_domain


class DomainForm(forms.ModelForm):
    fqdn = forms.CharField(max_length=253, min_length=2, strip=False, validators=[validate_deployment_domain])

    class Meta:
        fields = ["fqdn", "backend"]
        model = Domain


class DeploymentForm(forms.ModelForm):
    reconciled_attempts = forms.ModelMultipleChoiceField(
        queryset=Deployment.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="I checked the service and these unconfirmed attempts are safe to replace",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["domain"].disabled = True
        domain = self.initial.get("domain")
        if domain is not None:
            self.fields["reconciled_attempts"].queryset = Deployment.objects.filter(
                domain=domain, start_failed=True, reconciled=False
            )

    def clean_domain(self):
        domain = self.cleaned_data["domain"]
        validate_deployment_domain(domain.fqdn)
        return domain

    class Meta:
        fields = ["domain", "target"]
        model = Deployment
