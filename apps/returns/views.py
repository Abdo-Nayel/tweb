import json
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.codes import lookup_by_code, next_invoice_number
from apps.core.pagination import paginate_queryset
from apps.inventory.models import Product, Warehouse, ProductCategory
from apps.parties.models import Customer, Supplier
from apps.pharmacy.models import Branch
from apps.treasury.models import Bank
from apps.treasury.banks import banks_for_user
from apps.parties.customers import active_customers
from .models import ReturnDocument, ReturnLine, ReturnPayment


def _next_return():
    return next_invoice_number(ReturnDocument, 'return_number')


def _context_lists(user):
    return {
        'customers': active_customers(),
        'suppliers': Supplier.objects.filter(is_active=True).order_by('code'),
        'warehouses': Warehouse.objects.filter(is_active=True).select_related('branch').order_by('code'),
        'banks': banks_for_user(user),
    }


def _return_cart_json(obj):
    lines = obj.lines.select_related('product', 'product__brand').order_by('id')
    return {
        'return_number': obj.return_number,
        'subtotal': str(obj.subtotal),
        'discount': str(obj.discount),
        'grand_total': str(obj.grand_total),
        'line_count': lines.count(),
        'lines': [
            {
                'id': line.pk,
                'product_id': line.product_id,
                'name': line.product.name,
                'sku': line.product.sku,
                'quantity': str(line.quantity),
                'unit_price': str(line.unit_price),
                'line_total': str(line.line_total),
            }
            for line in lines
        ],
    }


def _products_for_pos():
    products = Product.objects.filter(is_active=True).select_related(
        'category', 'brand',
    ).annotate(stock_qty=Sum('stock_lots__quantity')).order_by('category__code', 'name')
    return [
        {
            'id': p.pk,
            'name': p.name,
            'sku': p.sku,
            'barcode': p.barcode or '',
            'sale_price': str(p.sale_price),
            'category_id': p.category_id,
            'category': p.category.name,
            'brand': p.brand.name if p.brand_id else '',
            'model': p.model_name or '',
            'storage': p.storage or '',
            'stock': str(p.stock_qty or 0),
        }
        for p in products
    ]


def _get_draft_return(pk):
    return get_object_or_404(
        ReturnDocument.objects.select_related('warehouse', 'customer', 'supplier'),
        pk=pk,
        status=ReturnDocument.Status.DRAFT,
    )


@login_required
def return_list(request):
    kind = request.GET.get('kind', '')
    items = ReturnDocument.objects.select_related(
        'warehouse', 'customer', 'supplier',
    ).order_by('-date', '-id')
    if kind in ('sales', 'purchase'):
        items = items.filter(kind=kind)
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'returns/return_list.html', {
        'page_title': 'مرتجعات الفواتير',
        'items': page_obj,
        'page_obj': page_obj,
        'kind': kind,
    })


@login_required
def product_lookup(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'found': False})
    product = Product.objects.filter(
        Q(barcode=q) | Q(sku=q) | Q(name__icontains=q),
        is_active=True,
    ).first()
    if not product:
        return JsonResponse({'found': False})
    return JsonResponse({
        'found': True,
        'id': product.pk,
        'name': product.name,
        'sku': product.sku,
        'sale_price': str(product.sale_price),
        'cost_price': str(product.cost_price),
    })


@login_required
def return_add(request):
    ctx = _context_lists(request.user)
    if request.method == 'POST':
        kind = request.POST.get('kind')
        if kind not in (ReturnDocument.Kind.SALES, ReturnDocument.Kind.PURCHASE):
            messages.error(request, 'اختر نوع المرتجع')
            return redirect('return_add')

        warehouse = get_object_or_404(Warehouse, pk=request.POST['warehouse'])
        branch_id = warehouse.branch_id

        customer_id = None
        supplier_id = None
        walk_in_name = ''
        walk_in_phone = ''

        if kind == ReturnDocument.Kind.SALES:
            party_type = request.POST.get('party_type', 'cash')
            if party_type == 'credit':
                customer_id = request.POST.get('customer')
                if not customer_id:
                    messages.error(request, 'اختر العميل')
                    return redirect('return_add')
            else:
                walk_in_name = request.POST.get('walk_in_name', '').strip()
                walk_in_phone = request.POST.get('walk_in_phone', '').strip()
        else:
            supplier_id = request.POST.get('supplier')
            if not supplier_id:
                messages.error(request, 'اختر المورد')
                return redirect('return_add')

        doc = ReturnDocument.objects.create(
            return_number=_next_return(),
            kind=kind,
            branch_id=branch_id,
            warehouse=warehouse,
            customer_id=customer_id,
            supplier_id=supplier_id,
            walk_in_name=walk_in_name,
            walk_in_phone=walk_in_phone,
            date=request.POST.get('date') or date.today(),
            created_by=request.user,
        )
        label = 'مبيعات' if kind == ReturnDocument.Kind.SALES else 'مشتريات'
        messages.success(request, f'مرتجع {label} {doc.return_number} — أضف الأصناف')
        return redirect('return_edit', pk=doc.pk)

    return render(request, 'returns/return_start.html', {
        'page_title': 'مرتجع فاتورة جديد',
        'today': date.today(),
        'open_drafts': ReturnDocument.objects.filter(status='draft').order_by('-created_at')[:10],
        **ctx,
    })


@login_required
@require_POST
def return_pos_add(request, pk):
    obj = _get_draft_return(pk)
    product = get_object_or_404(Product, pk=request.POST.get('product_id'), is_active=True)
    qty = Decimal(request.POST.get('quantity') or 1)
    if qty <= 0:
        return JsonResponse({'ok': False, 'error': 'الكمية يجب أن تكون أكبر من صفر'}, status=400)
    unit_price = request.POST.get('unit_price')
    price = Decimal(unit_price) if unit_price else product.sale_price
    line = obj.lines.filter(product=product).first()
    if line:
        line.quantity += qty
        line.save(update_fields=['quantity'])
    else:
        ReturnLine.objects.create(
            document=obj, product=product, quantity=qty, unit_price=price,
        )
    obj.recalculate()
    return JsonResponse({'ok': True, 'cart': _return_cart_json(obj)})


@login_required
@require_POST
def return_pos_remove(request, pk):
    obj = _get_draft_return(pk)
    ReturnLine.objects.filter(pk=request.POST.get('line_id'), document=obj).delete()
    obj.recalculate()
    return JsonResponse({'ok': True, 'cart': _return_cart_json(obj)})


@login_required
@require_POST
def return_pos_qty(request, pk):
    obj = _get_draft_return(pk)
    line = get_object_or_404(ReturnLine, pk=request.POST.get('line_id'), document=obj)
    qty = Decimal(request.POST.get('quantity') or 0)
    if qty <= 0:
        line.delete()
    else:
        line.quantity = qty
        line.save(update_fields=['quantity'])
    obj.recalculate()
    return JsonResponse({'ok': True, 'cart': _return_cart_json(obj)})


@login_required
def return_edit(request, pk):
    obj = get_object_or_404(
        ReturnDocument.objects.select_related('warehouse', 'customer', 'supplier'),
        pk=pk,
    )
    if obj.status == ReturnDocument.Status.POSTED:
        return redirect('return_detail', pk=pk)

    ctx = _context_lists(request.user)
    lines = obj.lines.select_related('product')
    payments = obj.payments.select_related('bank')
    paid = sum(p.amount for p in payments)
    remaining = obj.grand_total - paid

    if request.method == 'POST':
        obj.discount = Decimal(request.POST.get('discount') or 0)
        obj.notes = request.POST.get('notes', '')
        if obj.kind == ReturnDocument.Kind.SALES:
            obj.walk_in_name = request.POST.get('walk_in_name', obj.walk_in_name)
            obj.walk_in_phone = request.POST.get('walk_in_phone', obj.walk_in_phone)
            cid = request.POST.get('customer')
            if cid:
                obj.customer_id = cid
        else:
            sid = request.POST.get('supplier')
            if sid:
                obj.supplier_id = sid
        obj.save()
        obj.recalculate()

        obj.payments.all().delete()
        pay_types = request.POST.getlist('pay_type')
        pay_banks = request.POST.getlist('pay_bank')
        pay_amounts = request.POST.getlist('pay_amount')
        for i, amount in enumerate(pay_amounts):
            amt = Decimal(amount or 0)
            if amt <= 0:
                continue
            ptype = pay_types[i] if i < len(pay_types) else 'cash'
            bank_id = pay_banks[i] if i < len(pay_banks) else ''
            ReturnPayment.objects.create(
                document=obj,
                payment_type=ptype,
                bank_id=bank_id or None,
                amount=amt,
            )

        if 'save_post' in request.POST:
            if not obj.lines.exists():
                messages.error(request, 'أضف صنفاً واحداً على الأقل')
                return redirect('return_edit', pk=pk)
            try:
                with transaction.atomic():
                    obj.recalculate()
                    obj.post(user=request.user)
                messages.success(request, f'تم ترحيل {obj.return_number}')
                return redirect('return_detail', pk=pk)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('return_edit', pk=pk)

        messages.success(request, 'تم حفظ المسودة')
        return redirect('return_edit', pk=pk)

    refund_label = 'استرداد للعميل' if obj.kind == ReturnDocument.Kind.SALES else 'تحصيل من المورد'
    categories = ProductCategory.objects.filter(is_active=True).order_by('code')
    return render(request, 'returns/return_pos.html', {
        'page_title': f'{obj.return_number} — مرتجع',
        'obj': obj,
        'lines': lines,
        'payments': payments,
        'paid': paid,
        'remaining': remaining,
        'refund_label': refund_label,
        'categories': categories,
        'products_json': json.dumps(_products_for_pos(), ensure_ascii=False),
        'cart_json': json.dumps(_return_cart_json(obj), ensure_ascii=False),
        **ctx,
    })


@login_required
def return_detail(request, pk):
    obj = get_object_or_404(
        ReturnDocument.objects.select_related('warehouse', 'customer', 'supplier'),
        pk=pk,
    )
    return render(request, 'returns/return_detail.html', {
        'page_title': f'مرتجع {obj.return_number}',
        'obj': obj,
        'lines': obj.lines.select_related('product'),
        'payments': obj.payments.select_related('bank'),
    })
