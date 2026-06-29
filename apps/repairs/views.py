from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.core.codes import next_serial
from apps.core.pagination import paginate_queryset
from apps.inventory.models import Product, Warehouse
from apps.treasury.banks import banks_for_user
from .models import RepairOrder, RepairPart, RepairPayment


def _next_order_no():
    return next_serial(RepairOrder, 'order_no')


def _parse_decimal(raw, default='0'):
    text = str(raw).strip() if raw not in (None, '') else ''
    if not text:
        return Decimal(default)
    return Decimal(text)


@login_required
def repair_list(request):
    status = request.GET.get('status', '')
    items = RepairOrder.objects.select_related('warehouse').order_by('-date', '-id')
    if status:
        items = items.filter(status=status)
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'repairs/repair_list.html', {
        'page_title': 'أوامر الصيانة',
        'items': page_obj,
        'page_obj': page_obj,
        'status': status,
        'statuses': RepairOrder.Status.choices,
    })


@login_required
def repair_add(request):
    warehouses = Warehouse.objects.filter(is_active=True).order_by('code')
    products = Product.objects.filter(is_active=True).order_by('name')
    if request.method == 'POST':
        wh_id = request.POST.get('warehouse')
        if not wh_id:
            messages.error(request, 'اختر المخزن')
            return redirect('repair_add')
        wh = get_object_or_404(Warehouse, pk=wh_id)

        try:
            with transaction.atomic():
                order = RepairOrder.objects.create(
                    order_no=_next_order_no(),
                    date=request.POST.get('date') or date.today(),
                    customer_name=request.POST.get('customer_name', '').strip(),
                    customer_phone=request.POST.get('customer_phone', '').strip(),
                    device_desc=request.POST.get('device_desc', '').strip(),
                    problem=request.POST.get('problem', '').strip(),
                    labor_fee=_parse_decimal(request.POST.get('labor_fee'), '0'),
                    warehouse=wh,
                    notes=request.POST.get('notes', ''),
                    created_by=request.user,
                )
                _save_parts(request, order)
                order.recalculate()

                deposit = _parse_decimal(request.POST.get('deposit'), '0')
                if deposit > 0:
                    bank_id = request.POST.get('deposit_bank') or None
                    pay_type = 'bank' if bank_id else 'cash'
                    bank = get_object_or_404(banks_for_user(request.user), pk=bank_id) if bank_id else None
                    order.record_payment(deposit, pay_type=pay_type, bank=bank, is_deposit=True, user=request.user)

                order.deduct_stock_parts(user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('repair_add')

        messages.success(request, f'تم استلام الجهاز — أمر {order.order_no}')
        return redirect('repair_detail', pk=order.pk)

    return render(request, 'repairs/repair_form.html', {
        'page_title': 'استلام جهاز للصيانة',
        'today': date.today(),
        'warehouses': warehouses,
        'products': products,
        'banks': banks_for_user(request.user),
    })


def _save_parts(request, order):
    sources = request.POST.getlist('part_source')
    products = request.POST.getlist('part_product')
    ext_descs = request.POST.getlist('part_ext_desc')
    qtys = request.POST.getlist('part_qty')
    costs = request.POST.getlist('part_cost')
    order.part_lines.all().delete()
    for i, src in enumerate(sources):
        if src not in (RepairPart.Source.STOCK, RepairPart.Source.EXTERNAL):
            continue
        prod_id = products[i] if i < len(products) else ''
        ext = ext_descs[i] if i < len(ext_descs) else ''
        if src == RepairPart.Source.STOCK and not prod_id:
            continue
        if src == RepairPart.Source.EXTERNAL and not ext.strip():
            continue
        try:
            qty = _parse_decimal(qtys[i] if i < len(qtys) else '1', '1')
            cost = _parse_decimal(costs[i] if i < len(costs) else '0', '0')
        except Exception:
            continue
        if qty <= 0:
            continue
        if src == RepairPart.Source.STOCK and prod_id:
            RepairPart.objects.create(
                order=order, source=src, product_id=prod_id,
                quantity=qty, unit_cost=cost or Product.objects.get(pk=prod_id).cost_price,
            )
        elif src == RepairPart.Source.EXTERNAL and ext.strip():
            RepairPart.objects.create(
                order=order, source=src, ext_desc=ext.strip(),
                quantity=qty, unit_cost=cost,
            )


@login_required
def repair_detail(request, pk):
    order = get_object_or_404(
        RepairOrder.objects.select_related('warehouse'),
        pk=pk,
    )
    return render(request, 'repairs/repair_detail.html', {
        'page_title': f'صيانة {order.order_no}',
        'obj': order,
        'parts': order.part_lines.select_related('product'),
        'payments': order.payments.select_related('bank'),
        'banks': banks_for_user(request.user),
        'status_choices': RepairOrder.Status.choices,
    })


@login_required
def repair_complete(request, pk):
    order = get_object_or_404(RepairOrder, pk=pk)
    if order.status == RepairOrder.Status.DONE:
        return redirect('repair_detail', pk=pk)

    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount') or 0)
        pay_type = request.POST.get('pay_type', 'cash')
        bank_id = request.POST.get('bank') or None
        bank = get_object_or_404(banks_for_user(request.user), pk=bank_id) if bank_id else None

        with transaction.atomic():
            if amount > 0:
                order.record_payment(amount, pay_type=pay_type, bank=bank, user=request.user)
            order.status = RepairOrder.Status.DONE
            order.completed_at = timezone.now()
            order.save(update_fields=['status', 'completed_at'])

        messages.success(request, f'تم إكمال الصيانة — {order.order_no}')
        return redirect('repair_detail', pk=pk)

    return render(request, 'repairs/repair_complete.html', {
        'page_title': f'إكمال صيانة {order.order_no}',
        'obj': order,
        'banks': banks_for_user(request.user),
    })


@login_required
def repair_status(request, pk):
    order = get_object_or_404(RepairOrder, pk=pk)
    new_status = request.POST.get('status')
    if new_status in dict(RepairOrder.Status.choices):
        order.status = new_status
        order.save(update_fields=['status'])
        messages.success(request, 'تم تحديث حالة الصيانة')
    return redirect('repair_detail', pk=pk)
