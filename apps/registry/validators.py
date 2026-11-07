from django.core.exceptions import ValidationError
from django.core.validators import DomainNameValidator


def validate_deployment_domain(value):
    """Require an unambiguous ASCII DNS spelling without rewriting identifiers."""
    if not value.isascii() or value != value.lower() or value.endswith(".") or len(value) > 253:
        raise ValidationError("Enter a lowercase ASCII domain name without a trailing dot.", code="invalid")
    DomainNameValidator()(value)
