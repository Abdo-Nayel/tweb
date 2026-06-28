from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.codes import next_serial
from apps.core.pagination import paginate_queryset
from apps.inventory.models import Brand, Product, ProductCategory, Warehouse
from apps.pharmacy.models import ShopProfile
from apps.treasury.banks import banks_for_user
from .models import ExternalBuyback
from .services import create_product_from_buyback


def _next_doc_no():
    return next_serial(ExternalBuyback, 'doc_no')


def _resolve_product(request, amount, sale_price):
    mode = request.POST.get('product_mode', 'existing')
    if mode == 'new':
        if not request.POST.get('new_category') or not request.POST.get('new_brand'):
            raise ValueError('اختر الفئة والماركة لإنشاء صنف جديد')
        return create_product_from_buyback(request.POST, request.user, amount, sale_price)
    product_id = request.POST.get('product')
    if not product_id:
        raise ValueError('اختر الصنف أو فعّل إنشاء صنف جديد')
    return get_object_or_404(Product, pk=product_id, is_active=True)


@login_required
def buyback_list(request):
    items = ExternalBuyback.objects.select_related(
        'warehouse', 'product', 'bank',
    ).order_by('-date', '-id')
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'buyback/buyback_list.html', {
        'page_title': 'مشتريات من أفراد',
        'items': page_obj,
        'page_obj': page_obj,
    })


@login_required
def buyback_add(request):
    warehouses = Warehouse.objects.filter(is_active=True).order_by('code')
    categories = ProductCategory.objects.filter(is_active=True).order_by('code')
    products = Product.objects.filter(is_active=True).select_related('category', 'brand').order_by('name')
    banks = banks_for_user(request.user)

    if request.method == 'POST':
        warehouse = get_object_or_404(Warehouse, pk=request.POST['warehouse'])
        amount = Decimal(request.POST.get('purchase_amount') or 0)
        sale_price = Decimal(request.POST.get('sale_price') or 0)
        if amount <= 0:
            messages.error(request, 'أدخل مبلغ الشراء')
            return redirect('buyback_add')

        pay_type = request.POST.get('payment_type', 'cash')
        bank_id = request.POST.get('bank') or None
        bank = get_object_or_404(banks, pk=bank_id) if bank_id else None
        is_new_product = request.POST.get('product_mode') == 'new'

        try:
            with transaction.atomic():
                product = _resolve_product(request, amount, sale_price)
                serial = request.POST.get('serial_number', '').strip()
                if (product.is_serialized or is_new_product) and not serial:
                    raise ValueError('السيريال / IMEI مطلوب')

                doc = ExternalBuyback(
                    doc_no=_next_doc_no(),
                    date=request.POST.get('date') or date.today(),
                    branch_id=warehouse.branch_id,
                    warehouse=warehouse,
                    product=product,
                    seller_name=request.POST.get('seller_name', '').strip(),
                    seller_phone=request.POST.get('seller_phone', '').strip(),
                    national_id=request.POST.get('national_id', '').strip(),
                    serial_number=serial,
                    device_specs=request.POST.get('device_specs', '').strip(),
                    model_name=request.POST.get('model_name', '').strip(),
                    storage=request.POST.get('storage', '').strip(),
                    color=request.POST.get('color', '').strip(),
                    purchase_amount=amount,
                    sale_price=sale_price,
                    payment_type=pay_type,
                    bank=bank,
                    notes=request.POST.get('notes', ''),
                    created_by=request.user,
                )
                if request.FILES.get('id_card_photo'):
                    doc.id_card_photo = request.FILES['id_card_photo']
                doc.save()
                doc.post(user=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('buyback_add')

        messages.success(request, f'تم الشراء وإدخال المخزون — {doc.doc_no}')
        if is_new_product:
            messages.info(request, f'تم إنشاء صنف جديد: {product.sku} — {product.name}')
        action = request.POST.get('after_save', 'detail')
        if action == 'receipt':
            return redirect('buyback_receipt', pk=doc.pk)
        if action == 'declaration':
            return redirect('buyback_declaration', pk=doc.pk)
        return redirect('buyback_detail', pk=doc.pk)

    brands = Brand.objects.filter(is_active=True).order_by('name')
    return render(request, 'buyback/buyback_form.html', {
        'page_title': 'شراء من عميل خارجي',
        'today': date.today(),
        'warehouses': warehouses,
        'categories': categories,
        'brands': brands,
        'products': products,
        'banks': banks,
    })


@login_required
def buyback_detail(request, pk):
    obj = get_object_or_404(
        ExternalBuyback.objects.select_related('warehouse', 'product', 'product__brand', 'bank', 'created_by'),
        pk=pk,
    )
    return render(request, 'buyback/buyback_detail.html', {
        'page_title': f'شراء {obj.doc_no}',
        'obj': obj,
    })


@login_required
def buyback_receipt(request, pk):
    obj = get_object_or_404(
        ExternalBuyback.objects.select_related('warehouse', 'product', 'product__brand', 'bank', 'created_by'),
        pk=pk,
    )
    profile = ShopProfile.objects.first()
    return render(request, 'buyback/buyback_receipt.html', {
        'obj': obj,
        'profile': profile,
    })


@login_required
def buyback_declaration(request, pk):
    obj = get_object_or_404(
        ExternalBuyback.objects.select_related('warehouse', 'product', 'product__brand', 'created_by'),
        pk=pk,
    )
    profile = ShopProfile.objects.first()
    return render(request, 'buyback/buyback_declaration.html', {
        'obj': obj,
        'profile': profile,
        'today': date.today(),
    })
