from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from decimal import Decimal
from datetime import date

from apps.core.pagination import paginate_queryset
from apps.core.views import delete_confirm
from apps.core.delete_checks import supplier_blockers, customer_blockers
from apps.core.codes import next_serial
from apps.purchases.models import PurchaseInvoice
from apps.sales.models import SalesInvoice
from apps.treasury.models import Bank
from apps.treasury.banks import banks_for_user
from apps.parties.customers import active_customers
from .models import Supplier, Customer, SupplierPayment, CustomerPayment


def _next_code(model, prefix=None, field='code'):
    return next_serial(model, field)


@login_required
def supplier_list(request):
    q = request.GET.get('q', '')
    items = Supplier.objects.all()
    if q:
        items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'parties/supplier_list.html', {
        'page_title': 'الموردين', 'items': page_obj, 'page_obj': page_obj, 'q': q,
    })


@login_required
def supplier_form(request, pk=None):
    obj = get_object_or_404(Supplier, pk=pk) if pk else None
    if request.method == 'POST':
        data = {
            'code': request.POST.get('code') or _next_code(Supplier, 'SUP'),
            'name': request.POST['name'],
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
            'notes': request.POST.get('notes', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
        else:
            Supplier.objects.create(**data)
        messages.success(request, 'تم الحفظ')
        return redirect('supplier_list')
    return render(request, 'parties/supplier_form.html', {
        'page_title': 'مورد', 'obj': obj,
        'suggested_code': obj.code if obj else _next_code(Supplier, 'SUP'),
    })


@login_required
def customer_list(request):
    q = request.GET.get('q', '')
    items = Customer.objects.all()
    if q:
        items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'parties/customer_list.html', {
        'page_title': 'العملاء', 'items': page_obj, 'page_obj': page_obj, 'q': q,
    })


@login_required
def customer_form(request, pk=None):
    obj = get_object_or_404(Customer, pk=pk) if pk else None
    if request.method == 'POST':
        data = {
            'code': request.POST.get('code') or _next_code(Customer, 'CUS'),
            'name': request.POST['name'],
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
            'credit_limit': request.POST.get('credit_limit', 0) or 0,
            'notes': request.POST.get('notes', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
        else:
            Customer.objects.create(**data)
        messages.success(request, 'تم الحفظ')
        return redirect('customer_list')
    return render(request, 'parties/customer_form.html', {
        'page_title': 'عميل', 'obj': obj,
        'suggested_code': obj.code if obj else _next_code(Customer, 'CUS'),
    })


@login_required
def supplier_delete(request, pk):
    return delete_confirm(
        request, Supplier, pk, supplier_blockers, 'supplier_list', 'suppliers',
        object_label=lambda o: o.name, page_title='حذف مورد',
    )


@login_required
def customer_delete(request, pk):
    return delete_confirm(
        request, Customer, pk, customer_blockers, 'customer_list', 'customers',
        object_label=lambda o: o.name, page_title='حذف عميل',
    )


@login_required
def supplier_balances(request):
    q = request.GET.get('q', '')
    items = Supplier.objects.filter(is_active=True)
    if q:
        items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
    items = items.order_by('name')
    return render(request, 'parties/supplier_balances.html', {
        'page_title': 'أرصدة الموردين',
        'items': items,
        'q': q,
    })


@login_required
def supplier_statement(request):
    suppliers = Supplier.objects.filter(is_active=True).order_by('code')
    supplier_id = request.GET.get('supplier')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    supplier = get_object_or_404(Supplier, pk=supplier_id) if supplier_id else None
    entries = []
    opening_balance = Decimal('0')

    if supplier:
        all_entries = []
        invoices = PurchaseInvoice.objects.filter(
            supplier=supplier, status='posted',
        ).prefetch_related('payments')
        if date_from:
            invoices = invoices.filter(date__gte=date_from)
        if date_to:
            invoices = invoices.filter(date__lte=date_to)

        for inv in invoices.order_by('date', 'id'):
            all_entries.append({
                'date': inv.date,
                'ref': inv.invoice_number,
                'desc': 'فاتورة مشتريات',
                'debit': inv.grand_total,
                'credit': Decimal('0'),
            })
            for pay in inv.payments.all():
                all_entries.append({
                    'date': inv.date,
                    'ref': inv.invoice_number,
                    'desc': f'سداد فاتورة {pay.get_payment_type_display()}' + (f' — {pay.bank}' if pay.bank else ''),
                    'debit': Decimal('0'),
                    'credit': pay.amount,
                })

        pay_qs = SupplierPayment.objects.filter(supplier=supplier).select_related('bank')
        if date_from:
            pay_qs = pay_qs.filter(date__gte=date_from)
        if date_to:
            pay_qs = pay_qs.filter(date__lte=date_to)
        for sp in pay_qs.order_by('date', 'id'):
            all_entries.append({
                'date': sp.date,
                'ref': sp.reference,
                'desc': f'سداد مورد — {sp.get_payment_type_display()}' + (f' — {sp.bank}' if sp.bank else ''),
                'debit': Decimal('0'),
                'credit': sp.amount,
            })

        if date_from:
            prior_inv = PurchaseInvoice.objects.filter(
                supplier=supplier, status='posted', date__lt=date_from,
            ).prefetch_related('payments')
            for inv in prior_inv:
                opening_balance += inv.grand_total
                for pay in inv.payments.all():
                    opening_balance -= pay.amount
            prior_pay = SupplierPayment.objects.filter(supplier=supplier, date__lt=date_from)
            for sp in prior_pay:
                opening_balance -= sp.amount

        all_entries.sort(key=lambda e: (e['date'], e['ref']))
        running = opening_balance
        if date_from and opening_balance != 0:
            entries.append({
                'date': date_from,
                'ref': '—',
                'desc': 'رصيد افتتاحي للفترة',
                'debit': opening_balance if opening_balance > 0 else Decimal('0'),
                'credit': -opening_balance if opening_balance < 0 else Decimal('0'),
                'balance': running,
            })
        for e in all_entries:
            running += e['debit'] - e['credit']
            e['balance'] = running
            entries.append(e)

    return render(request, 'parties/supplier_statement.html', {
        'page_title': 'كشف حساب مورد',
        'suppliers': suppliers,
        'supplier': supplier,
        'entries': entries,
        'date_from': date_from or '',
        'date_to': date_to or '',
    })


@login_required
def supplier_payment(request):
    banks = banks_for_user(request.user)
    suppliers = Supplier.objects.filter(is_active=True).order_by('code')

    if request.method == 'POST':
        supplier = get_object_or_404(Supplier, pk=request.POST['supplier'])
        amount = Decimal(request.POST['amount'])
        payment_type = request.POST.get('payment_type', 'cash')
        bank_id = request.POST.get('bank') or None
        pay_date = request.POST.get('date') or date.today().isoformat()

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('supplier_payment')

        if payment_type == 'bank' and not bank_id:
            messages.error(request, 'اختر البنك')
            return redirect('supplier_payment')

        with transaction.atomic():
            payment = SupplierPayment(
                reference=next_serial(SupplierPayment, 'reference'),
                supplier=supplier,
                date=pay_date,
                amount=amount,
                payment_type=payment_type,
                bank_id=bank_id if payment_type == 'bank' else None,
                notes=request.POST.get('notes', ''),
                created_by=request.user,
            )
            payment.save()
            payment.apply()

        messages.success(request, f'تم تسجيل سداد {amount} للمورد {supplier.name}')
        from django.urls import reverse
        return redirect(f"{reverse('supplier_statement')}?supplier={supplier.pk}")

    preselect = request.GET.get('supplier')
    return render(request, 'parties/supplier_payment.html', {
        'page_title': 'سداد مورد',
        'suppliers': suppliers,
        'banks': banks,
        'today': date.today().isoformat(),
        'preselect_supplier': preselect,
    })


@login_required
def customer_balances(request):
    q = request.GET.get('q', '')
    items = Customer.objects.filter(is_active=True)
    if q:
        items = items.filter(Q(name__icontains=q) | Q(code__icontains=q) | Q(phone__icontains=q))
    items = items.order_by('code')
    return render(request, 'parties/customer_balances.html', {
        'page_title': 'أرصدة العملاء',
        'items': items,
        'q': q,
    })


@login_required
def customer_statement(request):
    customers = active_customers()
    customer_id = request.GET.get('customer')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    customer = get_object_or_404(Customer, pk=customer_id) if customer_id else None
    entries = []
    opening_balance = Decimal('0')

    if customer:
        all_entries = []
        invoices = SalesInvoice.objects.filter(
            customer=customer, status='posted', payment_type='credit',
        ).prefetch_related('payments')
        if date_from:
            invoices = invoices.filter(date__gte=date_from)
        if date_to:
            invoices = invoices.filter(date__lte=date_to)

        for inv in invoices.order_by('date', 'id'):
            all_entries.append({
                'date': inv.date,
                'ref': inv.invoice_number,
                'desc': 'فاتورة مبيعات آجل',
                'debit': inv.grand_total,
                'credit': Decimal('0'),
            })
            for pay in inv.payments.all():
                all_entries.append({
                    'date': inv.date,
                    'ref': inv.invoice_number,
                    'desc': f'تحصيل فاتورة {pay.get_payment_type_display()}' + (f' — {pay.bank}' if pay.bank else ''),
                    'debit': Decimal('0'),
                    'credit': pay.amount,
                })

        coll_qs = CustomerPayment.objects.filter(customer=customer).select_related('bank')
        if date_from:
            coll_qs = coll_qs.filter(date__gte=date_from)
        if date_to:
            coll_qs = coll_qs.filter(date__lte=date_to)
        for cp in coll_qs.order_by('date', 'id'):
            all_entries.append({
                'date': cp.date,
                'ref': cp.reference,
                'desc': f'تحصيل {cp.get_payment_type_display()}' + (f' — {cp.bank}' if cp.bank else ''),
                'debit': Decimal('0'),
                'credit': cp.amount,
            })

        if date_from:
            prior_inv = SalesInvoice.objects.filter(
                customer=customer, status='posted', payment_type='credit', date__lt=date_from,
            ).prefetch_related('payments')
            for inv in prior_inv:
                opening_balance += inv.grand_total
                for pay in inv.payments.all():
                    opening_balance -= pay.amount
            prior_coll = CustomerPayment.objects.filter(customer=customer, date__lt=date_from)
            for cp in prior_coll:
                opening_balance -= cp.amount

        all_entries.sort(key=lambda e: (e['date'], e['ref']))
        running = opening_balance
        if date_from and opening_balance != 0:
            entries.append({
                'date': date_from,
                'ref': '—',
                'desc': 'رصيد افتتاحي للفترة',
                'debit': opening_balance if opening_balance > 0 else Decimal('0'),
                'credit': -opening_balance if opening_balance < 0 else Decimal('0'),
                'balance': running,
            })
        for e in all_entries:
            running += e['debit'] - e['credit']
            e['balance'] = running
            entries.append(e)

    return render(request, 'parties/customer_statement.html', {
        'page_title': 'كشف حساب عميل',
        'customers': customers,
        'customer': customer,
        'entries': entries,
        'date_from': date_from or '',
        'date_to': date_to or '',
    })


@login_required
def customer_payment(request):
    banks = banks_for_user(request.user)
    customers = active_customers()

    if request.method == 'POST':
        customer = get_object_or_404(Customer, pk=request.POST['customer'])
        amount = Decimal(request.POST['amount'])
        payment_type = request.POST.get('payment_type', 'cash')
        bank_id = request.POST.get('bank') or None
        pay_date = request.POST.get('date') or date.today().isoformat()

        if amount <= 0:
            messages.error(request, 'المبلغ يجب أن يكون أكبر من صفر')
            return redirect('customer_payment')

        if payment_type == 'bank' and not bank_id:
            messages.error(request, 'اختر البنك')
            return redirect('customer_payment')

        with transaction.atomic():
            payment = CustomerPayment(
                reference=next_serial(CustomerPayment, 'reference'),
                customer=customer,
                date=pay_date,
                amount=amount,
                payment_type=payment_type,
                bank_id=bank_id if payment_type == 'bank' else None,
                notes=request.POST.get('notes', ''),
                created_by=request.user,
            )
            payment.save()
            payment.apply()

        messages.success(request, f'تم تحصيل {amount} من {customer.name}')
        from django.urls import reverse
        return redirect(f"{reverse('customer_statement')}?customer={customer.pk}")

    preselect = request.GET.get('customer')
    return render(request, 'parties/customer_payment.html', {
        'page_title': 'تحصيل من عميل',
        'customers': customers,
        'banks': banks,
        'today': date.today().isoformat(),
        'preselect_customer': preselect,
    })
