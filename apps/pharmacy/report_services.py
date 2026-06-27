from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from apps.core.branch_scope import user_branch_id
from apps.parties.models import CustomerPayment, SupplierPayment
from apps.purchases.models import PurchaseInvoice, PurchasePayment
from apps.returns.models import ReturnDocument
from apps.sales.models import SalesInvoice, SalesPayment
from apps.treasury.models import Expense
from apps.treasury.ledger_helpers import build_ledger_entries, cash_ledger_querysets, scope_branch


def _parse_range(date_from=None, date_to=None):
    today = timezone.localdate()
    date_from = date_from or today
    date_to = date_to or date_from
    if date_to < date_from:
        date_from, date_to = date_to, date_from
    return date_from, date_to


def _date_filter(qs, field, date_from, date_to):
    return qs.filter(**{f'{field}__gte': date_from, f'{field}__lte': date_to})


def _cash_payment_sum(user, model, invoice_field, date_from, date_to):
    qs = model.objects.filter(payment_type='cash', **{f'{invoice_field}__status': 'posted'})
    qs = scope_branch(user, qs, f'{invoice_field}__branch_id')
    qs = _date_filter(qs, f'{invoice_field}__date', date_from, date_to)
    return qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')


def build_daily_report(user, date_from=None, date_to=None):
    date_from, date_to = _parse_range(date_from, date_to)

    sales_qs = scope_branch(
        user,
        _date_filter(SalesInvoice.objects.filter(status='posted'), 'date', date_from, date_to),
        'branch_id',
    )
    purchases_qs = scope_branch(
        user,
        _date_filter(PurchaseInvoice.objects.filter(status='posted'), 'date', date_from, date_to),
        'branch_id',
    )
    returns_qs = scope_branch(
        user,
        _date_filter(ReturnDocument.objects.filter(status='posted'), 'date', date_from, date_to),
        'branch_id',
    )
    expenses_qs = scope_branch(
        user,
        _date_filter(Expense.objects.filter(bank__isnull=True), 'date', date_from, date_to),
        'created_by__branch_id',
    )
    customer_payments_qs = scope_branch(
        user,
        _date_filter(CustomerPayment.objects.filter(payment_type='cash'), 'date', date_from, date_to),
        'created_by__branch_id',
    )
    supplier_payments_qs = scope_branch(
        user,
        _date_filter(SupplierPayment.objects.filter(payment_type='cash'), 'date', date_from, date_to),
        'created_by__branch_id',
    )

    sales_total = sales_qs.aggregate(t=Sum('grand_total'))['t'] or Decimal('0')
    purchases_total = purchases_qs.aggregate(t=Sum('grand_total'))['t'] or Decimal('0')
    sales_returns_total = returns_qs.filter(kind='sales').aggregate(t=Sum('grand_total'))['t'] or Decimal('0')
    purchase_returns_total = returns_qs.filter(kind='purchase').aggregate(t=Sum('grand_total'))['t'] or Decimal('0')
    expenses_total = expenses_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    customer_collected = customer_payments_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    supplier_paid = supplier_payments_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    invoice_collections = _cash_payment_sum(user, SalesPayment, 'invoice', date_from, date_to)
    invoice_payments = _cash_payment_sum(user, PurchasePayment, 'invoice', date_from, date_to)

    cash_sets = cash_ledger_querysets(user, date_from.isoformat(), date_to.isoformat())
    cash_entries, cash_in, cash_out = build_ledger_entries(*cash_sets)
    net_cash = cash_in - cash_out

    movements = [
        {
            'date': e['date'],
            'ref': e['ref'],
            'desc': e['desc'],
            'in': e['in'],
            'out': e['out'],
        }
        for e in sorted(cash_entries, key=lambda x: (x['date'], x['ref']))
    ]

    return {
        'date_from': date_from,
        'date_to': date_to,
        'branch_id': user_branch_id(user),
        'summary': {
            'sales': sales_total,
            'purchases': purchases_total,
            'sales_returns': sales_returns_total,
            'purchase_returns': purchase_returns_total,
            'invoice_collections': invoice_collections,
            'invoice_payments': invoice_payments,
            'expenses': expenses_total,
            'customer_collected': customer_collected,
            'supplier_paid': supplier_paid,
            'cash_in': cash_in,
            'cash_out': cash_out,
            'net_cash': net_cash,
            'invoices_count': sales_qs.count() + purchases_qs.count(),
            'returns_count': returns_qs.count(),
        },
        'movements': movements,
        'total_in': cash_in,
        'total_out': cash_out,
        'net': net_cash,
    }
