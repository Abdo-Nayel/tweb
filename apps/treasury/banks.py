"""استعلامات البنوك — أسماء البنوك مشتركة لكل الفروع."""
from apps.treasury.models import Bank


def banks_for_user(user, *, active_only=True):
    qs = Bank.objects.all()
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.order_by('name', 'code')
