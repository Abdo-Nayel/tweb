from datetime import date
from decimal import Decimal

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F

from apps.inventory.models import Product
from apps.sales.models import SalesInvoice
from apps.parties.models import Customer, Supplier
from apps.core.dashboard_shortcuts import DASHBOARD_SHORTCUTS, DEFAULT_DASHBOARD_SHORTCUTS, SHORTCUTS_BY_KEY
from apps.core.permissions import user_can
from apps.treasury.models import Bank, CashBox


@login_required
def dashboard(request):
    today = date.today()
    low_stock = Product.objects.filter(is_active=True).annotate(
        total_qty=Sum('stock_lots__quantity')
    ).filter(total_qty__lt=F('min_stock')).count()

    today_sales = SalesInvoice.objects.filter(
        status='posted', date=today
    ).aggregate(total=Sum('grand_total'))['total'] or Decimal('0')

    customers_count = Customer.objects.filter(is_active=True).count()
    cash_balance = CashBox.get_main().balance
    bank_balance = Bank.objects.filter(is_active=True).aggregate(
        total=Sum('balance')
    )['total'] or Decimal('0')

    recent_sales = SalesInvoice.objects.filter(
        status='posted'
    ).select_related('customer').order_by('-date', '-id')[:5]

    shortcut_keys = request.user.dashboard_shortcuts or DEFAULT_DASHBOARD_SHORTCUTS
    dashboard_shortcuts = []
    for key in shortcut_keys:
        item = SHORTCUTS_BY_KEY.get(key)
        if not item:
            continue
        if request.user.is_superuser or user_can(request.user, item['module'], item['perm']):
            dashboard_shortcuts.append(item)

    context = {
        'page_title': 'لوحة التحكم',
        'low_stock': low_stock,
        'today_sales': today_sales,
        'customers_count': customers_count,
        'cash_balance': cash_balance,
        'bank_balance': bank_balance,
        'recent_sales': recent_sales,
        'dashboard_shortcuts': dashboard_shortcuts,
    }
    return render(request, 'dashboard/home.html', context)
