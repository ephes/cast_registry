from django import forms

from .models import Domain


class DomainForm(forms.ModelForm):
    fqdn = forms.CharField(max_length=255, min_length=2)

    class Meta:
        fields = ["fqdn"]
        model = Domain
