from datetime import date
from decimal import Decimal
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from apps.core.pagination import paginate_queryset
from apps.core.views import delete_confirm
from apps.core.codes import next_invoice_number, lookup_by_code
from apps.parties.models import Customer
from apps.parties.customers import active_customers
from apps.inventory.models import Product, Warehouse, ProductCategory
from apps.shop.models import Branch, ShopProfile, ReceiptSettings
from apps.treasury.models import Bank
from apps.treasury.banks import banks_for_user
from .models import SalesInvoice, SalesLine, SalesPayment


def _next_invoice():
    return next_invoice_number(SalesInvoice)


def _context_lists(user):
    return {
        'customers': active_customers(),
        'warehouses': Warehouse.objects.filter(is_active=True).select_related('branch').order_by('code'),
        'branches': Branch.objects.filter(is_active=True).order_by('code'),
        'banks': banks_for_user(user),
    }


def _invoice_cart_json(obj):
    lines = obj.lines.select_related('product', 'product__brand').order_by('id')
    return {
        'invoice_number': obj.invoice_number,
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
                'brand': line.product.brand.name if line.product.brand_id else '',
                'model': line.product.model_name or '',
                'quantity': str(line.quantity),
                'unit_price': str(line.unit_price),
                'discount': str(line.discount),
                'line_total': str(line.line_total),
            }
            for line in lines
        ],
    }


def _products_for_pos():
    products = Product.objects.filter(is_active=True).select_related(
        'category', 'brand',
    ).annotate(
        stock_qty=Sum('stock_lots__quantity'),
    ).order_by('category__code', 'name')
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


def _get_draft_invoice(pk, user):
    return get_object_or_404(
        SalesInvoice.objects.select_related('customer', 'warehouse', 'branch'),
        pk=pk,
        status=SalesInvoice.Status.DRAFT,
    )


@login_required
def sales_list(request):
    items = SalesInvoice.objects.select_related(
        'customer', 'warehouse', 'branch',
    ).prefetch_related('lines').order_by('-date', '-id')
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'sales/sales_list.html', {
        'page_title': 'فواتير المبيعات',
        'items': page_obj,
        'page_obj': page_obj,
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
        'barcode': product.barcode or '',
        'sale_price': str(product.sale_price),
    })


@login_required
def customer_lookup(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'found': False})
    c = lookup_by_code(Customer, q) or Customer.objects.filter(
        Q(name__icontains=q) | Q(code__icontains=q) | Q(phone__icontains=q),
        is_active=True,
    ).first()
    if not c:
        return JsonResponse({'found': False})
    return JsonResponse({'found': True, 'id': c.pk, 'code': c.code, 'name': c.name})


@login_required
def sales_add(request):
    """الخطوة ١: بدء فاتورة بيع — نقدي أو آجل."""
    ctx = _context_lists(request.user)
    profile = ShopProfile.objects.first()

    if request.method == 'POST':
        payment_type = request.POST.get('payment_type', 'cash')
        warehouse_id = request.POST['warehouse']
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
        branch_id = request.POST.get('branch') or warehouse.branch_id

        customer_id = None
        walk_in_name = ''
        walk_in_phone = ''

        if payment_type == 'credit':
            customer_id = request.POST.get('customer')
            if not customer_id:
                messages.error(request, 'اختر العميل للفاتورة الآجلة')
                return redirect('sales_add')
        else:
            walk_in_name = request.POST.get('walk_in_name', '').strip()
            walk_in_phone = request.POST.get('walk_in_phone', '').strip()

        inv = SalesInvoice.objects.create(
            invoice_number=_next_invoice(),
            branch_id=branch_id,
            customer_id=customer_id,
            walk_in_name=walk_in_name,
            walk_in_phone=walk_in_phone,
            warehouse_id=warehouse_id,
            date=request.POST.get('date') or date.today(),
            payment_type=payment_type,
            created_by=request.user,
            status=SalesInvoice.Status.DRAFT,
        )
        messages.success(request, f'فاتورة {inv.invoice_number} — نقطة البيع')
        return redirect('sales_edit', pk=inv.pk)

    return render(request, 'sales/sales_start.html', {
        'page_title': 'نقطة البيع',
        'today': date.today(),
        'open_drafts': SalesInvoice.objects.filter(status='draft').order_by('-created_at', '-id')[:10],
        **ctx,
    })


@login_required
@require_POST
def sales_pos_add(request, pk):
    obj = _get_draft_invoice(pk, request.user)
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
        SalesLine.objects.create(
            invoice=obj,
            product=product,
            quantity=qty,
            unit_price=price,
            unit_cost=product.cost_price,
        )
    obj.recalculate()
    return JsonResponse({'ok': True, 'cart': _invoice_cart_json(obj)})


@login_required
@require_POST
def sales_pos_remove(request, pk):
    obj = _get_draft_invoice(pk, request.user)
    SalesLine.objects.filter(pk=request.POST.get('line_id'), invoice=obj).delete()
    obj.recalculate()
    return JsonResponse({'ok': True, 'cart': _invoice_cart_json(obj)})


@login_required
@require_POST
def sales_pos_qty(request, pk):
    obj = _get_draft_invoice(pk, request.user)
    line = get_object_or_404(SalesLine, pk=request.POST.get('line_id'), invoice=obj)
    qty = Decimal(request.POST.get('quantity') or 0)
    if qty <= 0:
        line.delete()
    else:
        line.quantity = qty
        line.save(update_fields=['quantity'])
    obj.recalculate()
    return JsonResponse({'ok': True, 'cart': _invoice_cart_json(obj)})


@login_required
def sales_form(request, pk):
    """الخطوة ٢: POS — إضافة أصناف + تحصيل + ترحيل."""
    obj = get_object_or_404(
        SalesInvoice.objects.select_related('customer', 'warehouse', 'branch'),
        pk=pk,
    )
    if obj.status == SalesInvoice.Status.POSTED:
        return redirect('sales_detail', pk=pk)

    ctx = _context_lists(request.user)

    if request.method == 'POST':
        if 'add_line' in request.POST:
            product = get_object_or_404(Product, pk=request.POST['product_id'])
            qty = Decimal(request.POST.get('quantity') or 0)
            if qty <= 0:
                messages.error(request, 'الكمية يجب أن تكون أكبر من صفر')
            else:
                SalesLine.objects.create(
                    invoice=obj,
                    product=product,
                    quantity=qty,
                    unit_price=Decimal(request.POST.get('unit_price') or product.sale_price),
                    unit_cost=product.cost_price,
                    discount=Decimal(request.POST.get('line_discount') or 0),
                )
                obj.recalculate()
                messages.success(request, f'تم إضافة {product.name}')
            return redirect('sales_edit', pk=pk)

        if 'remove_line' in request.POST:
            SalesLine.objects.filter(pk=request.POST['line_id'], invoice=obj).delete()
            obj.recalculate()
            return redirect('sales_edit', pk=pk)

        if 'save_draft' in request.POST or 'save_post' in request.POST:
            obj.notes = request.POST.get('notes', '')
            obj.discount = Decimal(request.POST.get('discount') or 0)
            obj.walk_in_name = request.POST.get('walk_in_name', obj.walk_in_name)
            obj.walk_in_phone = request.POST.get('walk_in_phone', obj.walk_in_phone)
            if obj.payment_type == SalesInvoice.PaymentType.CREDIT:
                cid = request.POST.get('customer')
                if cid:
                    obj.customer_id = cid
            obj.save()
            obj.recalculate()
            obj.payments.all().delete()
            for ptype, bank_id, amount in zip(
                request.POST.getlist('pay_type'),
                request.POST.getlist('pay_bank'),
                request.POST.getlist('pay_amount'),
            ):
                if amount and Decimal(amount) > 0:
                    SalesPayment.objects.create(
                        invoice=obj,
                        payment_type=ptype or 'cash',
                        bank_id=bank_id or None,
                        amount=amount,
                    )
            obj.recalculate()

            if 'save_post' in request.POST:
                if not obj.lines.exists():
                    messages.error(request, 'السلة فارغة — أضف منتجاً واحداً على الأقل')
                    return redirect('sales_edit', pk=pk)
                if obj.payment_type == SalesInvoice.PaymentType.CREDIT and not obj.customer_id:
                    messages.error(request, 'الفاتورة الآجلة تحتاج عميلاً')
                    return redirect('sales_edit', pk=pk)
                try:
                    with transaction.atomic():
                        obj.post(user=request.user)
                    n = obj.lines.count()
                    messages.success(
                        request,
                        f'تم إتمام البيع — فاتورة رقم {obj.invoice_number} '
                        f'({n} صنف) بإجمالي {obj.grand_total} ج.م',
                    )
                    receipt_settings = ReceiptSettings.get_solo()
                    if receipt_settings.auto_print:
                        from django.urls import reverse
                        return redirect(reverse('sales_receipt', kwargs={'pk': obj.pk}) + '?auto=1')
                    return redirect('sales_list')
                except Exception as e:
                    messages.error(request, str(e))
                    return redirect('sales_edit', pk=pk)
            messages.success(request, 'تم حفظ المسودة')
            return redirect('sales_edit', pk=pk)

    lines = obj.lines.select_related('product', 'product__brand').all()
    payments = obj.payments.select_related('bank').all()
    paid = sum(p.amount for p in payments)
    remaining = obj.grand_total - paid
    categories = ProductCategory.objects.filter(is_active=True).order_by('code')

    return render(request, 'sales/sales_pos.html', {
        'page_title': 'نقطة البيع',
        'pos_mode': True,
        'obj': obj,
        'lines': lines,
        'payments': payments,
        'paid': paid,
        'remaining': remaining,
        'categories': categories,
        'products_json': json.dumps(_products_for_pos(), ensure_ascii=False),
        'cart_json': json.dumps(_invoice_cart_json(obj), ensure_ascii=False),
        **ctx,
    })


@login_required
def sales_detail(request, pk):
    obj = get_object_or_404(
        SalesInvoice.objects.select_related('customer', 'warehouse', 'branch'),
        pk=pk,
    )
    lines = obj.lines.select_related('product').all()
    payments = obj.payments.select_related('bank').all()
    paid = sum(p.amount for p in payments)
    return render(request, 'sales/sales_detail.html', {
        'page_title': f'فاتورة {obj.invoice_number}',
        'obj': obj,
        'lines': lines,
        'payments': payments,
        'paid': paid,
        'remaining': obj.grand_total - paid,
        'is_draft': obj.status == SalesInvoice.Status.DRAFT,
    })


@login_required
def sales_items_report(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    q = request.GET.get('q', '').strip()
    customer_id = request.GET.get('customer')

    lines = SalesLine.objects.filter(
        invoice__status='posted',
    ).select_related('invoice', 'product', 'invoice__customer', 'invoice__warehouse')

    if date_from:
        lines = lines.filter(invoice__date__gte=date_from)
    if date_to:
        lines = lines.filter(invoice__date__lte=date_to)
    if customer_id:
        lines = lines.filter(invoice__customer_id=customer_id)
    if q:
        lines = lines.filter(
            Q(product__name__icontains=q)
            | Q(product__sku__icontains=q)
            | Q(product__barcode__icontains=q)
            | Q(invoice__invoice_number__icontains=q)
        )

    lines = lines.order_by('-invoice__date', '-invoice__id')
    grand_qty = sum(l.quantity for l in lines)
    grand_sales = sum(l.line_total for l in lines)
    page_obj = paginate_queryset(request, lines, per_page=50)

    return render(request, 'sales/sales_items_report.html', {
        'page_title': 'تقرير مبيعات بالأصناف',
        'rows': page_obj,
        'page_obj': page_obj,
        'customers': active_customers(),
        'date_from': date_from,
        'date_to': date_to,
        'q': q,
        'selected_customer': customer_id,
        'grand_qty': grand_qty,
        'grand_sales': grand_sales,
    })


@login_required
def sales_profit_report(request):
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    payment_type = request.GET.get('payment_type', '')

    invoices = SalesInvoice.objects.filter(
        status='posted',
    ).select_related('customer', 'warehouse').prefetch_related('lines__product')

    if date_from:
        invoices = invoices.filter(date__gte=date_from)
    if date_to:
        invoices = invoices.filter(date__lte=date_to)
    if payment_type:
        invoices = invoices.filter(payment_type=payment_type)

    rows = []
    total_sales = Decimal('0')
    total_cost = Decimal('0')
    total_profit = Decimal('0')

    for inv in invoices.order_by('-date', '-id'):
        cost = inv.total_cost
        profit = inv.gross_profit
        rows.append({
            'invoice': inv,
            'sales': inv.grand_total,
            'cost': cost,
            'profit': profit,
        })
        total_sales += inv.grand_total
        total_cost += cost
        total_profit += profit

    page_obj = paginate_queryset(request, rows, per_page=50)
    return render(request, 'sales/sales_profit_report.html', {
        'page_title': 'تقرير أرباح المبيعات',
        'rows': page_obj,
        'page_obj': page_obj,
        'date_from': date_from,
        'date_to': date_to,
        'payment_type': payment_type,
        'total_sales': total_sales,
        'total_cost': total_cost,
        'total_profit': total_profit,
    })


@login_required
def sales_reopen(request, pk):
    obj = get_object_or_404(SalesInvoice, pk=pk)
    if obj.status != SalesInvoice.Status.POSTED:
        return redirect('sales_edit', pk=pk)
    try:
        with transaction.atomic():
            obj.unpost(user=request.user)
        messages.info(request, 'تم فتح الفاتورة للتعديل — أعد الترحيل بعد الانتهاء')
    except Exception as e:
        messages.error(request, str(e))
        return redirect('sales_detail', pk=pk)
    return redirect('sales_edit', pk=pk)


@login_required
def sales_receipt(request, pk):
    obj = get_object_or_404(
        SalesInvoice.objects.select_related('customer', 'warehouse', 'branch', 'created_by'),
        pk=pk,
    )
    lines = obj.lines.select_related('product').all()
    payments = obj.payments.select_related('bank').all()
    paid = sum(p.amount for p in payments)
    profile = ShopProfile.objects.first()
    receipt_cfg = ReceiptSettings.get_solo()
    logo_url = None
    if receipt_cfg.show_logo:
        if receipt_cfg.receipt_logo:
            logo_url = receipt_cfg.receipt_logo.url
        elif receipt_cfg.use_shop_logo and profile and profile.logo:
            logo_url = profile.logo.url
    return render(request, 'sales/sales_receipt.html', {
        'obj': obj,
        'lines': lines,
        'payments': payments,
        'paid': paid,
        'remaining': obj.grand_total - paid,
        'change': max(paid - obj.grand_total, Decimal('0')),
        'profile': profile,
        'receipt': receipt_cfg,
        'logo_url': logo_url,
    })


@login_required
def sales_delete(request, pk):
    obj = get_object_or_404(SalesInvoice, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if obj.status == SalesInvoice.Status.POSTED:
                    obj.unpost(user=request.user)
                label = obj.invoice_number
                obj.delete()
            messages.success(request, f'تم حذف الفاتورة {label}')
        except Exception as e:
            messages.error(request, str(e))
        return redirect('sales_list')

    return render(request, 'partials/delete_confirm.html', {
        'page_title': 'حذف فاتورة مبيعات',
        'object': obj,
        'object_label': obj.invoice_number,
        'blockers': [],
        'cancel_url_name': 'sales_list',
        'extra_warning': 'سيتم إلغاء حركات المخزون والتحصيل المرتبطة بالفاتورة.' if obj.status == 'posted' else '',
    })
