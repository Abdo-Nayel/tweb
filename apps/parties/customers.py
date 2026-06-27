"""استعلامات العملاء للقوائم المنسدلة."""
from apps.parties.models import Customer


def active_customers():
    return Customer.objects.filter(is_active=True).order_by('name')
