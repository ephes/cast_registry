from django import forms

from .models import Domain


class DomainForm(forms.ModelForm):
    class Meta:
        fields = ["fqdn"]
        model = Domain
