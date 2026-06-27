from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from decimal import Decimal

from apps.core.pagination import paginate_queryset
from apps.core.views import delete_confirm
from apps.core.delete_checks import expense_blockers
from apps.core.ledger_export import export_ledger_excel, export_ledger_pdf
from .models import ExpenseCategory, Expense, Bank, CashBox
from .banks import banks_for_user
from .ledger_helpers import build_ledger_entries, cash_ledger_querysets, bank_ledger_querysets


def _parse_dates(request):
    return request.GET.get('date_from', ''), request.GET.get('date_to', '')


@login_required
def expense_list(request):
    q = request.GET.get('q', '')
    items = Expense.objects.select_related('category', 'bank').order_by('-date')
    if q:
        items = items.filter(Q(description__icontains=q) | Q(category__name__icontains=q))
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'treasury/expense_list.html', {
        'page_title': 'المصروفات',
        'items': page_obj,
        'page_obj': page_obj,
        'q': q,
    })


@login_required
def expense_form(request, pk=None):
    obj = get_object_or_404(Expense, pk=pk) if pk else None
    categories = ExpenseCategory.objects.filter(is_active=True)
    banks = banks_for_user(request.user)
    if request.method == 'POST':
        data = {
            'category_id': request.POST['category'],
            'bank_id': request.POST.get('bank') or None,
            'amount': request.POST['amount'],
            'date': request.POST['date'],
            'description': request.POST.get('description', ''),
        }
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
            messages.success(request, 'تم تحديث المصروف')
        else:
            with transaction.atomic():
                expense = Expense.objects.create(**data, created_by=request.user)
                if expense.bank_id:
                    expense.bank.balance -= expense.amount
                    expense.bank.save(update_fields=['balance'])
                else:
                    cash = CashBox.get_main()
                    cash.balance -= expense.amount
                    cash.save(update_fields=['balance'])
            messages.success(request, 'تم تسجيل المصروف')
        return redirect('expense_list')
    return render(request, 'treasury/expense_form.html', {
        'page_title': 'تعديل مصروف' if obj else 'تسجيل مصروف',
        'obj': obj,
        'categories': categories,
        'banks': banks,
    })


@login_required
def expense_delete(request, pk):
    return delete_confirm(
        request, Expense, pk, expense_blockers, 'expense_list', 'expenses',
        object_label=lambda o: str(o), page_title='حذف مصروف',
    )


@login_required
def cash_ledger(request):
    date_from, date_to = _parse_dates(request)
    cash = CashBox.get_main()
    branch_scoped = bool(getattr(request.user, 'branch_id', None))

    sets = cash_ledger_querysets(request.user, date_from, date_to)
    entries, total_in, total_out = build_ledger_entries(*sets)
    net_balance = total_in - total_out
    current_balance = net_balance if branch_scoped else cash.balance

    export_fmt = request.GET.get('export')
    title = f'كشف الخزنة النقدية — {cash.name}'
    if export_fmt == 'excel':
        return export_ledger_excel(
            entries, total_in, total_out, net_balance, current_balance,
            title, 'cash-ledger.xlsx',
        )
    if export_fmt == 'pdf':
        return export_ledger_pdf(
            entries, total_in, total_out, net_balance, current_balance,
            title, 'cash-ledger.pdf',
        )

    return render(request, 'treasury/cash_ledger.html', {
        'page_title': f'كشف الخزنة النقدية — {cash.name}',
        'cash': cash,
        'current_balance': current_balance,
        'branch_scoped': branch_scoped,
        'entries': entries,
        'date_from': date_from,
        'date_to': date_to,
        'total_in': total_in,
        'total_out': total_out,
        'net_balance': net_balance,
    })


@login_required
def bank_ledger(request):
    date_from, date_to = _parse_dates(request)
    bank_id = request.GET.get('bank')
    bank_q = request.GET.get('q', '').strip()
    banks = banks_for_user(request.user)

    if bank_q and not bank_id:
        match = banks.filter(Q(name__icontains=bank_q) | Q(code__icontains=bank_q)).first()
        if match:
            bank_id = str(match.pk)

    bank = get_object_or_404(Bank, pk=bank_id) if bank_id else banks.first()

    entries = []
    total_in = Decimal('0')
    total_out = Decimal('0')
    branch_scoped = bool(getattr(request.user, 'branch_id', None))
    if bank:
        sets = bank_ledger_querysets(request.user, bank, date_from, date_to)
        entries, total_in, total_out = build_ledger_entries(*sets)

    net_balance = total_in - total_out
    current_balance = net_balance if branch_scoped else (bank.balance if bank else Decimal('0'))

    export_fmt = request.GET.get('export')
    if bank and export_fmt == 'excel':
        return export_ledger_excel(
            entries, total_in, total_out, net_balance, current_balance,
            f'كشف بنك — {bank.name}', 'bank-ledger.xlsx',
        )
    if bank and export_fmt == 'pdf':
        return export_ledger_pdf(
            entries, total_in, total_out, net_balance, current_balance,
            f'كشف بنك — {bank.name}', 'bank-ledger.pdf',
        )

    return render(request, 'treasury/bank_ledger.html', {
        'page_title': f'كشف بنك — {bank.name}' if bank else 'كشف البنوك',
        'bank': bank,
        'banks': banks,
        'current_balance': current_balance,
        'branch_scoped': branch_scoped,
        'entries': entries,
        'date_from': date_from,
        'date_to': date_to,
        'bank_q': bank_q,
        'selected_bank': bank_id or (str(bank.pk) if bank else ''),
        'total_in': total_in,
        'total_out': total_out,
        'net_balance': net_balance,
    })


@login_required
def treasury_ledger(request):
    """إعادة توجيه للخزنة النقدية."""
    return redirect('cash_ledger')
