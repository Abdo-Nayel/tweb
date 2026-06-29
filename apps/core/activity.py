import re

from apps.shop.models import ActivityLog


def _post_val(post, key, default=''):
    raw = post.get(key) if post else None
    if raw is None or raw == '':
        return default
    return raw


def _post_str(post, key, default=''):
    return str(_post_val(post, key, default)).strip()


def _fmt_money(val):
    try:
        from decimal import Decimal
        d = Decimal(str(val or 0))
        return f'{d:.2f} ج.م'
    except Exception:
        return f'{val} ج.م'


_TREASURY_KIND_LABELS = {
    'cash_in': 'إيداع نقدي',
    'cash_out': 'سحب نقدي',
    'bank_in': 'إيداع بنك',
    'bank_out': 'سحب بنك',
    'c2b': 'تحويل نقد → بنك',
    'b2c': 'تحويل بنك → نقد',
}


def log_activity(request, action, section='', description='', object_ref=''):
    user = getattr(request, 'user', None)
    if user and not user.is_authenticated:
        user = None
    ip = request.META.get('REMOTE_ADDR') if request else None
    log = ActivityLog.objects.create(
        user=user,
        username=user.username if user else '—',
        action=action,
        section=section[:80] if section else '',
        description=description[:500] if description else '',
        object_ref=object_ref[:120] if object_ref else '',
        ip_address=ip,
        branch_id=getattr(user, 'branch_id', None) if user else None,
    )
    try:
        from apps.core.telegram_notify import notify_activity
        from apps.shop.models import TelegramSettings
        cfg = TelegramSettings.get_solo()
        if action == ActivityLog.Action.LOGIN and not cfg.notify_on_login:
            return log
        action_label = dict(ActivityLog.Action.choices).get(action, action)
        notify_activity(log, action_label)
    except Exception:
        pass
    return log


def log_from_request(request):
    if request.method != 'POST' or not request.user.is_authenticated:
        return
    path = request.path.rstrip('/') or '/'
    if path in ('/', '/logout'):
        return

    action, section, description, object_ref = _describe_request(request, path)
    log_activity(request, action, section=section, description=description, object_ref=object_ref)


def _describe_request(request, path):
    post = request.POST
    action = ActivityLog.Action.UPDATE
    section = _section_from_path(path)
    description = 'تعديل بيانات'
    object_ref = ''

    if 'delete' in path:
        action = ActivityLog.Action.DELETE
        description = 'حذف سجل'
    elif '/add' in path or path.endswith('/add'):
        action = ActivityLog.Action.CREATE

    # ─── مشتريات ───
    m = re.match(r'^/purchases/(\d+)/edit$', path)
    if m:
        inv_id = m.group(1)
        inv = _get_purchase_invoice(inv_id)
        ref = inv.invoice_number if inv else f'#{inv_id}'
        object_ref = ref
        section = 'المشتريات'
        if 'add_line' in post:
            action = ActivityLog.Action.CREATE
            product = _get_product(post.get('product_id'))
            pname = product.name if product else 'صنف'
            description = f'إضافة «{pname}» لفاتورة مشتريات رقم {ref}'
        elif 'remove_line' in post:
            action = ActivityLog.Action.DELETE
            description = f'حذف بند من فاتورة مشتريات رقم {ref}'
        elif 'save_post' in post:
            action = ActivityLog.Action.POST
            if inv:
                n = inv.lines.count()
                description = (
                    f'ترحيل فاتورة مشتريات {ref} — '
                    f'المورد: {inv.supplier.name} — {n} صنف — إجمالي {_fmt_money(inv.grand_total)}'
                )
            else:
                description = f'ترحيل فاتورة مشتريات رقم {ref}'
        elif 'save_draft' in post:
            action = ActivityLog.Action.UPDATE
            description = f'حفظ مسودة فاتورة مشتريات رقم {ref}'
        else:
            description = f'تعديل فاتورة مشتريات رقم {ref}'
        return action, section, description, object_ref

    if path in ('/purchases/add', '/purchases/start'):
        action = ActivityLog.Action.CREATE
        description = 'بدء فاتورة مشتريات جديدة'
        return action, 'المشتريات', description, object_ref

    # ─── مبيعات ───
    m = re.match(r'^/sales/(\d+)/edit$', path)
    if m:
        inv_id = m.group(1)
        inv = _get_sales_invoice(inv_id)
        ref = inv.invoice_number if inv else f'#{inv_id}'
        object_ref = ref
        section = 'المبيعات'
        if 'add_line' in post:
            action = ActivityLog.Action.CREATE
            product = _get_product(post.get('product_id'))
            pname = product.name if product else 'صنف'
            description = f'إضافة «{pname}» لفاتورة مبيعات رقم {ref}'
        elif 'remove_line' in post:
            action = ActivityLog.Action.DELETE
            description = f'حذف بند من فاتورة مبيعات رقم {ref}'
        elif 'save_post' in post:
            action = ActivityLog.Action.POST
            if inv:
                buyer = inv.receipt_buyer_display if hasattr(inv, 'receipt_buyer_display') else '—'
                description = (
                    f'ترحيل فاتورة مبيعات {ref} — عميل: {buyer} — '
                    f'{inv.lines.count()} صنف — إجمالي {_fmt_money(inv.grand_total)}'
                )
            else:
                description = f'ترحيل فاتورة مبيعات {ref}'
        elif 'save_draft' in post:
            description = f'حفظ مسودة فاتورة مبيعات رقم {ref}'
        else:
            description = f'تعديل فاتورة مبيعات رقم {ref}'
        return action, section, description, object_ref

    if path in ('/sales/add', '/sales/start'):
        action = ActivityLog.Action.CREATE
        description = 'بدء فاتورة مبيعات جديدة'
        return action, 'المبيعات', description, object_ref

    m = re.match(r'^/sales/(\d+)/pos/(add|remove|qty)$', path)
    if m:
        inv = _get_sales_invoice(m.group(1))
        ref = inv.invoice_number if inv else f'#{m.group(1)}'
        product = _get_product(post.get('product_id'))
        ops = {'add': 'إضافة', 'remove': 'حذف', 'qty': 'تعديل كمية'}
        pname = product.name if product else 'صنف'
        return ActivityLog.Action.UPDATE, 'المبيعات', f'{ops.get(m.group(2), "تعديل")} «{pname}» — POS {ref}', ref

    # ─── مرتجعات ───
    m = re.match(r'^/returns/(\d+)/edit$', path)
    if m:
        doc = _get_return_doc(m.group(1))
        ref = doc.return_number if doc else f'#{m.group(1)}'
        if 'save_post' in post:
            action = ActivityLog.Action.POST
            if doc:
                description = (
                    f'ترحيل مرتجع {ref} — {doc.get_kind_display()} — '
                    f'{doc.party_display} — إجمالي {_fmt_money(doc.grand_total)}'
                )
            else:
                description = f'ترحيل مرتجع {ref}'
        else:
            description = f'تعديل مرتجع {ref}'
        return action, 'المرتجعات', description, ref

    m = re.match(r'^/returns/(\d+)/pos/(add|remove|qty)$', path)
    if m:
        product = _get_product(post.get('product_id'))
        pname = product.name if product else 'صنف'
        return ActivityLog.Action.UPDATE, 'المرتجعات', f'POS مرتجع — {pname}', f'#{m.group(1)}'

    # ─── صيانة ───
    if path == '/repairs/add':
        customer = _post_str(post, 'customer_name')
        phone = _post_str(post, 'customer_phone')
        device = _post_str(post, 'device_desc')
        problem = _post_str(post, 'problem')
        labor = _post_str(post, 'labor_fee', '0')
        deposit = _post_str(post, 'deposit', '0')
        wh_name = _get_warehouse_name(post.get('warehouse'))
        parts = [
            f'استلام جهاز — عميل: {customer} — ت: {phone}',
            f'جهاز: {device}',
        ]
        if problem:
            parts.append(f'عطل: {problem}')
        parts.append(f'مخزن: {wh_name} — أجر: {_fmt_money(labor)}')
        if float(deposit or 0) > 0:
            bank = _post_str(post, 'deposit_bank')
            pay = 'بنك' if bank else 'نقدي'
            parts.append(f'عربون: {_fmt_money(deposit)} ({pay})')
        ref = _latest_repair_ref(customer, phone)
        return ActivityLog.Action.CREATE, 'الصيانة', ' | '.join(parts), ref

    m = re.match(r'^/repairs/(\d+)/complete$', path)
    if m:
        order = _get_repair_order(m.group(1))
        ref = order.order_no if order else f'#{m.group(1)}'
        amount = _post_str(post, 'amount', '0')
        pay_type = 'بنك' if _post_str(post, 'bank') else 'نقدي'
        if order:
            desc = (
                f'إكمال صيانة — {order.customer_name} — جهاز: {order.device_desc} — '
                f'إجمالي {_fmt_money(order.total)} — تحصيل {_fmt_money(amount)} ({pay_type}) — '
                f'مدفوع {_fmt_money(order.paid)}'
            )
        else:
            desc = f'إكمال صيانة — تحصيل {_fmt_money(amount)} ({pay_type})'
        return ActivityLog.Action.POST, 'الصيانة', desc, ref

    m = re.match(r'^/repairs/(\d+)/status$', path)
    if m:
        order = _get_repair_order(m.group(1))
        ref = order.order_no if order else f'#{m.group(1)}'
        status = _post_str(post, 'status')
        return ActivityLog.Action.UPDATE, 'الصيانة', f'تغيير حالة الصيانة → {status}', ref

    # ─── شراء من فرد ───
    if path == '/buyback/add':
        seller = _post_str(post, 'seller_name')
        phone = _post_str(post, 'seller_phone')
        amt = _post_str(post, 'purchase_amount', '0')
        device = _post_str(post, 'device_desc')
        mode = _post_str(post, 'product_mode', 'existing')
        extra = ' + إنشاء صنف جديد' if mode == 'new' else ''
        ref = _latest_buyback_ref(seller)
        desc = (
            f'شراء جهاز من فرد — البائع: {seller}'
            f'{f" — ت: {phone}" if phone else ""}'
            f'{f" — {device}" if device else ""}'
            f' — {_fmt_money(amt)}{extra}'
        )
        return ActivityLog.Action.POST, 'مشتريات أفراد', desc, ref

    # ─── خزينة ───
    if path in ('/treasury/cash/', '/treasury/bank/'):
        kind = _post_str(post, 'kind')
        kind_label = _TREASURY_KIND_LABELS.get(kind, kind)
        amt = _post_str(post, 'amount', '0')
        notes = _post_str(post, 'notes')
        bank_name = _get_bank_name(post.get('bank'))
        label = 'نقدية' if 'cash' in path else 'بنك'
        parts = [f'{kind_label} — {_fmt_money(amt)}', f'قناة: {label}']
        if bank_name:
            parts.append(f'بنك: {bank_name}')
        if notes:
            parts.append(f'ملاحظة: {notes}')
        return ActivityLog.Action.CREATE, 'الخزينة', ' | '.join(parts), object_ref

    # ─── مخزون ───
    if path == '/inventory/products/add':
        action = ActivityLog.Action.CREATE
        name = _post_str(post, 'name')
        sku = _post_str(post, 'sku')
        cost = _post_str(post, 'cost_price', '0')
        sale = _post_str(post, 'sale_price', '0')
        parts = [f'إضافة منتج: {name}']
        if sku:
            parts.append(f'كود: {sku}')
        parts.append(f'تكلفة {_fmt_money(cost)} — بيع {_fmt_money(sale)}')
        return action, 'المخزون', ' | '.join(parts), sku or name

    m = re.match(r'^/inventory/products/(\d+)/edit$', path)
    if m:
        product = _get_product(m.group(1))
        pname = product.name if product else m.group(1)
        description = f'تعديل بيانات المنتج «{pname}»'
        return action, 'المخزون', description, object_ref

    if path == '/inventory/opening-stock':
        product = _get_product(post.get('product'))
        pname = product.name if product else 'صنف'
        qty = _post_str(post, 'quantity', '0')
        wh_name = _get_warehouse_name(post.get('warehouse'))
        action = ActivityLog.Action.CREATE
        description = f'رصيد افتتاحي — {pname} — كمية {qty} — مخزن {wh_name}'
        return action, 'المخزون', description, product.sku if product else ''

    if '/inventory/categories' in path:
        description = 'تعديل فئات المنتجات' if '/edit' in path else 'إضافة فئة منتجات'
        if action != ActivityLog.Action.DELETE and '/add' in path:
            action = ActivityLog.Action.CREATE
        return action, 'المخزون', description, object_ref

    if '/inventory/companies' in path:
        description = 'تعديل ماركة' if '/edit' in path else 'إضافة ماركة'
        if '/add' in path:
            action = ActivityLog.Action.CREATE
        return action, 'المخزون', description, object_ref

    if '/inventory/warehouses' in path:
        description = 'تعديل مخزن' if '/edit' in path else 'إضافة مخزن'
        if '/add' in path:
            action = ActivityLog.Action.CREATE
        return action, 'المخزون', description, object_ref

    # ─── أطراف ───
    if '/parties/customers' in path:
        if 'payment' in path:
            amt = _post_str(post, 'amount', '0')
            cust = _post_str(post, 'customer') or _get_customer_name(post.get('customer'))
            description = f'تحصيل من عميل {cust} — {_fmt_money(amt)}'
        elif '/add' in path:
            action = ActivityLog.Action.CREATE
            description = f'إضافة عميل: {_post_str(post, "name")} — ت: {_post_str(post, "phone")}'
        else:
            description = f'تعديل عميل: {_post_str(post, "name")}'
        return action, 'العملاء', description, object_ref

    if '/parties/suppliers' in path:
        if 'payment' in path:
            amt = _post_str(post, 'amount', '0')
            sup = _get_supplier_name(post.get('supplier'))
            description = f'سداد لمورد {sup} — {_fmt_money(amt)}'
        elif '/add' in path:
            action = ActivityLog.Action.CREATE
            description = f'إضافة مورد: {_post_str(post, "name")} — ت: {_post_str(post, "phone")}'
        else:
            description = f'تعديل مورد: {_post_str(post, "name")}'
        return action, 'الموردين', description, object_ref

    if '/treasury/expenses' in path:
        if '/add' in path:
            action = ActivityLog.Action.CREATE
            amt = _post_str(post, 'amount', '0')
            description = f'مصروف {_fmt_money(amt)} — {_post_str(post, "description")}'
        else:
            description = 'تعديل مصروف'
        return action, 'الخزينة', description, object_ref

    # ─── إعدادات ───
    if path == '/settings/shop':
        description = 'حفظ بيانات المحل'
        return action, 'الإعدادات', description, object_ref
    if path == '/settings/receipt':
        description = 'حفظ إعدادات إيصال البيع'
        return action, 'الإعدادات', description, object_ref
    if path == '/settings/barcode':
        description = 'حفظ إعدادات ليبل الباركود'
        return action, 'الإعدادات', description, object_ref
    if path == '/settings/telegram':
        description = 'حفظ إعدادات تليجرام'
        return action, 'الإعدادات', description, object_ref
    if '/settings/users' in path:
        if '/add' in path:
            action = ActivityLog.Action.CREATE
            description = 'إضافة مستخدم جديد'
        elif 'delete' in path:
            description = 'حذف مستخدم'
        else:
            description = 'تعديل صلاحيات مستخدم'
        return action, 'الإعدادات', description, object_ref
    if '/settings/banks' in path:
        description = 'إضافة بنك' if '/add' in path else 'تعديل بيانات بنك'
        if '/add' in path:
            action = ActivityLog.Action.CREATE
        return action, 'الإعدادات', description, object_ref

    # ─── افتراضي ───
    if 'save_post' in post or 'post' in post:
        action = ActivityLog.Action.POST
        description = f'ترحيل عملية في قسم {section}'
    elif action == ActivityLog.Action.CREATE:
        description = f'إضافة سجل في قسم {section}'
    elif action == ActivityLog.Action.DELETE:
        description = f'حذف سجل من قسم {section}'
    else:
        description = f'تعديل بيانات في قسم {section}'

    return action, section, description, object_ref


def _section_from_path(path):
    mapping = [
        ('/sales', 'المبيعات'),
        ('/purchases', 'المشتريات'),
        ('/returns', 'المرتجعات'),
        ('/repairs', 'الصيانة'),
        ('/buyback', 'مشتريات أفراد'),
        ('/parties/customers', 'العملاء'),
        ('/parties/suppliers', 'الموردين'),
        ('/parties', 'الأطراف'),
        ('/inventory', 'المخزون'),
        ('/treasury', 'الخزينة'),
        ('/settings', 'الإعدادات'),
        ('/dashboard', 'لوحة التحكم'),
    ]
    for prefix, label in mapping:
        if path.startswith(prefix):
            return label
    return 'النظام'


def _get_purchase_invoice(pk):
    try:
        from apps.purchases.models import PurchaseInvoice
        return PurchaseInvoice.objects.select_related('supplier').filter(pk=pk).first()
    except Exception:
        return None


def _get_sales_invoice(pk):
    try:
        from apps.sales.models import SalesInvoice
        return SalesInvoice.objects.filter(pk=pk).first()
    except Exception:
        return None


def _get_product(pk):
    if not pk:
        return None
    try:
        from apps.inventory.models import Product
        return Product.objects.filter(pk=pk).only('name', 'sku').first()
    except Exception:
        return None


def _get_warehouse_name(pk):
    if not pk:
        return '—'
    try:
        from apps.inventory.models import Warehouse
        wh = Warehouse.objects.filter(pk=pk).only('name').first()
        return wh.name if wh else '—'
    except Exception:
        return '—'


def _get_bank_name(pk):
    if not pk:
        return ''
    try:
        from apps.treasury.models import Bank
        b = Bank.objects.filter(pk=pk).only('name').first()
        return b.name if b else ''
    except Exception:
        return ''


def _get_customer_name(pk):
    if not pk:
        return '—'
    try:
        from apps.parties.models import Customer
        c = Customer.objects.filter(pk=pk).only('name').first()
        return c.name if c else '—'
    except Exception:
        return '—'


def _get_supplier_name(pk):
    if not pk:
        return '—'
    try:
        from apps.parties.models import Supplier
        s = Supplier.objects.filter(pk=pk).only('name').first()
        return s.name if s else '—'
    except Exception:
        return '—'


def _get_repair_order(pk):
    try:
        from apps.repairs.models import RepairOrder
        return RepairOrder.objects.filter(pk=pk).first()
    except Exception:
        return None


def _latest_repair_ref(customer, phone):
    try:
        from apps.repairs.models import RepairOrder
        q = RepairOrder.objects.order_by('-id')
        if phone:
            q = q.filter(customer_phone=phone)
        elif customer:
            q = q.filter(customer_name=customer)
        order = q.first()
        return order.order_no if order else ''
    except Exception:
        return ''


def _latest_buyback_ref(seller):
    try:
        from apps.buyback.models import ExternalBuyback
        doc = ExternalBuyback.objects.filter(seller_name=seller).order_by('-id').first()
        return doc.doc_no if doc else ''
    except Exception:
        return ''


def _get_return_doc(pk):
    try:
        from apps.returns.models import ReturnDocument
        return ReturnDocument.objects.select_related('customer', 'supplier').filter(pk=pk).first()
    except Exception:
        return None
