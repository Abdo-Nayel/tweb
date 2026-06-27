from decimal import Decimal

from apps.purchases.models import PurchasePayment
from apps.sales.models import SalesPayment
from apps.parties.models import SupplierPayment, CustomerPayment
from apps.returns.models import ReturnDocument, ReturnPayment
from apps.core.branch_scope import user_branch_id


def filter_by_date(qs, date_field, date_from, date_to):
    if date_from:
        qs = qs.filter(**{f'{date_field}__gte': date_from})
    if date_to:
        qs = qs.filter(**{f'{date_field}__lte': date_to})
    return qs


def scope_branch(user, qs, field):
    branch_id = user_branch_id(user)
    if branch_id:
        return qs.filter(**{field: branch_id})
    return qs


def build_ledger_entries(
    pay_out_qs, exp_qs, sup_pay_qs, pay_in_qs=None, cust_pay_qs=None,
    ret_out_qs=None, ret_in_qs=None,
):
    entries = []
    pay_in_qs = pay_in_qs or []
    cust_pay_qs = cust_pay_qs or []
    ret_out_qs = ret_out_qs or []
    ret_in_qs = ret_in_qs or []

    for pay in pay_out_qs:
        entries.append({
            'date': pay.invoice.date,
            'ref': pay.invoice.invoice_number,
            'desc': f'سداد مشتريات — {pay.invoice.supplier.name}',
            'out': pay.amount,
            'in': Decimal('0'),
        })
    for sp in sup_pay_qs:
        entries.append({
            'date': sp.date,
            'ref': sp.reference,
            'desc': f'سداد مورد — {sp.supplier.name}',
            'out': sp.amount,
            'in': Decimal('0'),
        })
    for exp in exp_qs:
        entries.append({
            'date': exp.date,
            'ref': getattr(exp.category, 'code', exp.category.name),
            'desc': exp.description or exp.category.name,
            'out': exp.amount,
            'in': Decimal('0'),
        })
    for pay in pay_in_qs:
        entries.append({
            'date': pay.invoice.date,
            'ref': pay.invoice.invoice_number,
            'desc': f'تحصيل مبيعات — {pay.invoice.ledger_label}',
            'out': Decimal('0'),
            'in': pay.amount,
        })
    for cp in cust_pay_qs:
        entries.append({
            'date': cp.date,
            'ref': cp.reference,
            'desc': f'تحصيل عميل — {cp.customer.name}',
            'out': Decimal('0'),
            'in': cp.amount,
        })
    for rp in ret_out_qs:
        entries.append({
            'date': rp.document.date,
            'ref': rp.document.return_number,
            'desc': f'استرداد مرتجع — {rp.document.party_display}',
            'out': rp.amount,
            'in': Decimal('0'),
        })
    for rp in ret_in_qs:
        entries.append({
            'date': rp.document.date,
            'ref': rp.document.return_number,
            'desc': f'تحصيل مرتجع — {rp.document.party_display}',
            'out': Decimal('0'),
            'in': rp.amount,
        })
    entries.sort(key=lambda e: e['date'], reverse=True)
    total_in = sum(e['in'] for e in entries)
    total_out = sum(e['out'] for e in entries)
    return entries, total_in, total_out


def cash_ledger_querysets(user, date_from='', date_to=''):
    from apps.treasury.models import Expense

    pay_out_qs = PurchasePayment.objects.filter(
        invoice__status='posted', payment_type='cash',
    ).select_related('invoice__supplier')
    pay_out_qs = scope_branch(user, pay_out_qs, 'invoice__branch_id')
    pay_out_qs = filter_by_date(pay_out_qs, 'invoice__date', date_from, date_to)

    pay_in_qs = SalesPayment.objects.filter(
        invoice__status='posted', payment_type='cash',
    ).select_related('invoice', 'invoice__customer')
    pay_in_qs = scope_branch(user, pay_in_qs, 'invoice__branch_id')
    pay_in_qs = filter_by_date(pay_in_qs, 'invoice__date', date_from, date_to)

    sup_pay_qs = SupplierPayment.objects.filter(payment_type='cash').select_related('supplier')
    sup_pay_qs = scope_branch(user, sup_pay_qs, 'created_by__branch_id')
    sup_pay_qs = filter_by_date(sup_pay_qs, 'date', date_from, date_to)

    cust_pay_qs = CustomerPayment.objects.filter(payment_type='cash').select_related('customer')
    cust_pay_qs = scope_branch(user, cust_pay_qs, 'created_by__branch_id')
    cust_pay_qs = filter_by_date(cust_pay_qs, 'date', date_from, date_to)

    exp_qs = Expense.objects.filter(bank__isnull=True).select_related('category')
    exp_qs = scope_branch(user, exp_qs, 'created_by__branch_id')
    exp_qs = filter_by_date(exp_qs, 'date', date_from, date_to)

    ret_out_qs = ReturnPayment.objects.filter(
        document__status='posted',
        document__kind=ReturnDocument.Kind.SALES,
        payment_type='cash',
    ).select_related('document')
    ret_out_qs = scope_branch(user, ret_out_qs, 'document__branch_id')
    ret_out_qs = filter_by_date(ret_out_qs, 'document__date', date_from, date_to)

    ret_in_qs = ReturnPayment.objects.filter(
        document__status='posted',
        document__kind=ReturnDocument.Kind.PURCHASE,
        payment_type='cash',
    ).select_related('document')
    ret_in_qs = scope_branch(user, ret_in_qs, 'document__branch_id')
    ret_in_qs = filter_by_date(ret_in_qs, 'document__date', date_from, date_to)

    return pay_out_qs, exp_qs, sup_pay_qs, pay_in_qs, cust_pay_qs, ret_out_qs, ret_in_qs


def bank_ledger_querysets(user, bank, date_from='', date_to=''):
    from apps.treasury.models import Expense

    pay_out_qs = PurchasePayment.objects.filter(
        invoice__status='posted', payment_type='bank', bank=bank,
    ).select_related('invoice__supplier')
    pay_out_qs = scope_branch(user, pay_out_qs, 'invoice__branch_id')
    pay_out_qs = filter_by_date(pay_out_qs, 'invoice__date', date_from, date_to)

    pay_in_qs = SalesPayment.objects.filter(
        invoice__status='posted', payment_type='bank', bank=bank,
    ).select_related('invoice', 'invoice__customer')
    pay_in_qs = scope_branch(user, pay_in_qs, 'invoice__branch_id')
    pay_in_qs = filter_by_date(pay_in_qs, 'invoice__date', date_from, date_to)

    sup_pay_qs = SupplierPayment.objects.filter(payment_type='bank', bank=bank).select_related('supplier')
    sup_pay_qs = scope_branch(user, sup_pay_qs, 'created_by__branch_id')
    sup_pay_qs = filter_by_date(sup_pay_qs, 'date', date_from, date_to)

    cust_pay_qs = CustomerPayment.objects.filter(payment_type='bank', bank=bank).select_related('customer')
    cust_pay_qs = scope_branch(user, cust_pay_qs, 'created_by__branch_id')
    cust_pay_qs = filter_by_date(cust_pay_qs, 'date', date_from, date_to)

    exp_qs = Expense.objects.filter(bank=bank).select_related('category')
    exp_qs = scope_branch(user, exp_qs, 'created_by__branch_id')
    exp_qs = filter_by_date(exp_qs, 'date', date_from, date_to)

    ret_out_qs = ReturnPayment.objects.filter(
        document__status='posted',
        document__kind=ReturnDocument.Kind.SALES,
        payment_type='bank', bank=bank,
    ).select_related('document')
    ret_out_qs = scope_branch(user, ret_out_qs, 'document__branch_id')
    ret_out_qs = filter_by_date(ret_out_qs, 'document__date', date_from, date_to)

    ret_in_qs = ReturnPayment.objects.filter(
        document__status='posted',
        document__kind=ReturnDocument.Kind.PURCHASE,
        payment_type='bank', bank=bank,
    ).select_related('document')
    ret_in_qs = scope_branch(user, ret_in_qs, 'document__branch_id')
    ret_in_qs = filter_by_date(ret_in_qs, 'document__date', date_from, date_to)

    return pay_out_qs, exp_qs, sup_pay_qs, pay_in_qs, cust_pay_qs, ret_out_qs, ret_in_qs
