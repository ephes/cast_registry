from django import forms

from .models import Deployment, Domain


class DomainForm(forms.ModelForm):
    fqdn = forms.CharField(max_length=255, min_length=2)

    class Meta:
        fields = ["fqdn"]
        model = Domain


class DeploymentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["domain"].disabled = True

    class Meta:
        fields = ["domain", "target"]
        model = Deployment
