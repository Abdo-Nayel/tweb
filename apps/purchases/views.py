from datetime import date
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse

from apps.core.pagination import paginate_queryset
from apps.core.views import delete_confirm
from apps.core.delete_checks import purchase_invoice_blockers
from apps.parties.models import Supplier
from apps.inventory.models import Product, Warehouse
from apps.pharmacy.models import Branch, PharmacyProfile
from apps.treasury.models import Bank
from apps.treasury.banks import banks_for_user
from .models import PurchaseInvoice, PurchaseLine, PurchasePayment


from apps.core.codes import next_serial, next_invoice_number


def _next_invoice():
    return next_invoice_number(PurchaseInvoice)


def _context_lists(user):
    return {
        'suppliers': Supplier.objects.all().order_by('code'),
        'warehouses': Warehouse.objects.filter(is_active=True).select_related('branch').order_by('code'),
        'branches': Branch.objects.filter(is_active=True).order_by('code'),
        'banks': banks_for_user(user),
    }


@login_required
def purchase_list(request):
    items = PurchaseInvoice.objects.select_related(
        'supplier', 'warehouse', 'branch',
    ).order_by('-date', '-id')
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'purchases/purchase_list.html', {
        'page_title': 'فواتير المشتريات',
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
        'cost_price': str(product.cost_price),
        'sale_price': str(product.sale_price),
    })


@login_required
def supplier_lookup(request):
    from apps.core.codes import lookup_by_code
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'found': False})
    s = lookup_by_code(Supplier, q) or Supplier.objects.filter(
        Q(name__icontains=q) | Q(code__icontains=q)
    ).first()
    if not s:
        return JsonResponse({'found': False})
    return JsonResponse({'found': True, 'id': s.pk, 'code': s.code, 'name': s.name})


@login_required
def purchase_add(request):
    """الخطوة ١: اختيار الفرع والمخزن والمورد وبدء الفاتورة."""
    ctx = _context_lists(request.user)
    profile = PharmacyProfile.objects.first()

    if request.method == 'POST':
        branch_id = request.POST.get('branch') or None
        warehouse_id = request.POST['warehouse']
        supplier_id = request.POST['supplier']
        warehouse = get_object_or_404(Warehouse, pk=warehouse_id)
        if not branch_id and warehouse.branch_id:
            branch_id = warehouse.branch_id

        inv = PurchaseInvoice.objects.create(
            invoice_number=_next_invoice(),
            branch_id=branch_id,
            supplier_id=supplier_id,
            warehouse_id=warehouse_id,
            date=request.POST.get('date') or date.today(),
            currency=profile.currency if profile else 'ج.م',
            created_by=request.user,
            status=PurchaseInvoice.Status.DRAFT,
        )
        messages.success(request, f'تم بدء الفاتورة {inv.invoice_number} — أضف الأصناف ثم احفظ')
        return redirect('purchase_edit', pk=inv.pk)

    return render(request, 'purchases/purchase_start.html', {
        'page_title': 'فاتورة مشتريات جديدة',
        'today': date.today(),
        **ctx,
    })


@login_required
def purchase_form(request, pk):
    """الخطوة ٢: إضافة أصناف + حفظ وترحيل."""
    obj = get_object_or_404(
        PurchaseInvoice.objects.select_related('supplier', 'warehouse', 'branch'),
        pk=pk,
    )
    if obj.status == PurchaseInvoice.Status.POSTED:
        messages.warning(request, 'الفاتورة مرحّلة ولا يمكن تعديلها')
        return redirect('purchase_list')

    ctx = _context_lists(request.user)

    if request.method == 'POST':
        if 'add_line' in request.POST:
            product = get_object_or_404(Product, pk=request.POST['product_id'])
            qty = Decimal(request.POST.get('quantity') or 0)
            if qty <= 0:
                messages.error(request, 'الكمية يجب أن تكون أكبر من صفر')
            else:
                PurchaseLine.objects.create(
                    invoice=obj,
                    product=product,
                    quantity=qty,
                    unit_cost=Decimal(request.POST.get('unit_cost') or product.cost_price),
                    sale_price=Decimal(request.POST.get('sale_price') or product.sale_price),
                    expiry_date=request.POST.get('expiry_date') or None,
                    batch_number=request.POST.get('batch_number', ''),
                )
                obj.recalculate()
                messages.success(request, f'تم إضافة {product.name}')
            return redirect('purchase_edit', pk=pk)

        if 'remove_line' in request.POST:
            PurchaseLine.objects.filter(pk=request.POST['line_id'], invoice=obj).delete()
            obj.recalculate()
            messages.success(request, 'تم حذف البند')
            return redirect('purchase_edit', pk=pk)

        if 'save_draft' in request.POST or 'save_post' in request.POST:
            obj.notes = request.POST.get('notes', '')
            obj.discount = Decimal(request.POST.get('discount') or 0)
            obj.tax = Decimal(request.POST.get('tax') or 0)
            obj.save()
            obj.payments.all().delete()
            for ptype, bank_id, amount in zip(
                request.POST.getlist('pay_type'),
                request.POST.getlist('pay_bank'),
                request.POST.getlist('pay_amount'),
            ):
                if amount and Decimal(amount) > 0:
                    PurchasePayment.objects.create(
                        invoice=obj,
                        payment_type=ptype or 'cash',
                        bank_id=bank_id or None,
                        amount=amount,
                    )
            obj.recalculate()

            if 'save_post' in request.POST:
                if not obj.lines.exists():
                    messages.error(request, 'أضف صنفاً واحداً على الأقل قبل الترحيل')
                    return redirect('purchase_edit', pk=pk)
                try:
                    with transaction.atomic():
                        obj.post(user=request.user)
                    messages.success(request, 'تم حفظ وترحيل الفاتورة — المخزون والمورد محدّثان')
                    return redirect('purchase_list')
                except Exception as e:
                    messages.error(request, str(e))
                    return redirect('purchase_edit', pk=pk)
            messages.success(request, 'تم حفظ المسودة')
            return redirect('purchase_edit', pk=pk)

    lines = obj.lines.select_related('product').all()
    payments = obj.payments.select_related('bank').all()
    remaining = obj.grand_total - sum(p.amount for p in payments)

    return render(request, 'purchases/purchase_workflow.html', {
        'page_title': f'فاتورة {obj.invoice_number}',
        'obj': obj,
        'lines': lines,
        'payments': payments,
        'remaining': remaining,
        **ctx,
    })


@login_required
def purchase_delete(request, pk):
    return delete_confirm(
        request, PurchaseInvoice, pk, purchase_invoice_blockers, 'purchase_list', 'purchases',
        object_label=lambda o: o.invoice_number, page_title='حذف فاتورة مشتريات',
    )
