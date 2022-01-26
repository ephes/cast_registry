from django import forms

from .models import Domain


class OddNumberForm(forms.Form):
    number = forms.IntegerField()


class DomainForm(forms.ModelForm):
    class Meta:
        fields = ["fqdn"]
        model = Domain
