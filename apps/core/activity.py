import re

from apps.shop.models import ActivityLog


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
        notify_activity(log.username, action_label, log.section, log.description, log.object_ref)
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
                    f'ترحيل فاتورة مشتريات رقم {ref} — '
                    f'المورد: {inv.supplier.name} — {n} صنف — الإجمالي {inv.grand_total} ج.م'
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
                description = (
                    f'ترحيل فاتورة مبيعات رقم {ref} — '
                    f'الإجمالي {inv.grand_total} ج.م'
                )
            else:
                description = f'ترحيل فاتورة مبيعات رقم {ref}'
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
        action = ActivityLog.Action.UPDATE
        if 'save_post' in post:
            action = ActivityLog.Action.POST
            description = f'ترحيل مرتجع رقم {m.group(1)}'
        else:
            description = f'تعديل مرتجع رقم {m.group(1)}'
        return action, 'المرتجعات', description, object_ref

    m = re.match(r'^/returns/(\d+)/pos/(add|remove|qty)$', path)
    if m:
        product = _get_product(post.get('product_id'))
        pname = product.name if product else 'صنف'
        return ActivityLog.Action.UPDATE, 'المرتجعات', f'POS مرتجع — {pname}', f'#{m.group(1)}'

    # ─── صيانة ───
    if path == '/repairs/add':
        return ActivityLog.Action.CREATE, 'الصيانة', 'استلام جهاز للصيانة', object_ref
    m = re.match(r'^/repairs/(\d+)/complete$', path)
    if m:
        return ActivityLog.Action.POST, 'الصيانة', f'إكمال صيانة #{m.group(1)}', object_ref

    # ─── شراء من فرد ───
    if path == '/buyback/add':
        seller = post.get('seller_name', '').strip()
        amt = post.get('purchase_amount', '')
        mode = post.get('product_mode', 'existing')
        extra = ' + صنف جديد' if mode == 'new' else ''
        return ActivityLog.Action.POST, 'مشتريات أفراد', f'شراء من {seller} — {amt} ج.م{extra}', object_ref

    # ─── خزينة ───
    if path in ('/treasury/cash/', '/treasury/bank/'):
        kind = post.get('kind', '')
        amt = post.get('amount', '')
        label = 'نقدية' if 'cash' in path else 'بنك'
        return ActivityLog.Action.CREATE, 'الخزينة', f'حركة {label}: {kind} — {amt} ج.م', object_ref

    # ─── مخزون ───
    if path == '/inventory/products/add':
        action = ActivityLog.Action.CREATE
        name = post.get('name', '').strip()
        description = f'إضافة منتج جديد{f" — {name}" if name else ""}'
        return action, 'المخزون', description, object_ref

    m = re.match(r'^/inventory/products/(\d+)/edit$', path)
    if m:
        product = _get_product(m.group(1))
        pname = product.name if product else m.group(1)
        description = f'تعديل بيانات المنتج «{pname}»'
        return action, 'المخزون', description, object_ref

    if path == '/inventory/opening-stock':
        product = _get_product(post.get('product'))
        pname = product.name if product else 'صنف'
        action = ActivityLog.Action.CREATE
        description = f'تسجيل رصيد افتتاحي للمنتج «{pname}»'
        return action, 'المخزون', description, object_ref

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
            description = 'تسجيل تحصيل من عميل'
        elif '/add' in path:
            action = ActivityLog.Action.CREATE
            description = 'إضافة عميل جديد'
        else:
            description = 'تعديل بيانات عميل'
        return action, 'العملاء', description, object_ref

    if '/parties/suppliers' in path:
        if 'payment' in path:
            description = 'تسجيل سداد لمورد'
        elif '/add' in path:
            action = ActivityLog.Action.CREATE
            description = 'إضافة مورد جديد'
        else:
            description = 'تعديل بيانات مورد'
        return action, 'الموردين', description, object_ref

    # ─── خزينة ───
    if '/treasury/expenses' in path:
        if '/add' in path:
            action = ActivityLog.Action.CREATE
            description = 'تسجيل مصروف جديد'
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
