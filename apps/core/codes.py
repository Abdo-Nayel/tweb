import re


def _numeric_value(code):
    if code is None:
        return 0
    digits = re.sub(r'\D', '', str(code))
    return int(digits) if digits else 0


def next_serial(model, field='code'):
    """الكود التالي: 1, 2, 3, ..."""
    max_num = 0
    for val in model.objects.values_list(field, flat=True):
        max_num = max(max_num, _numeric_value(val))
    return str(max_num + 1)


def next_invoice_number(model, field='invoice_number'):
    """رقم فاتورة تسلسلي: 1, 2, 3, ..."""
    return next_serial(model, field)


def lookup_by_code(model, code, field='code'):
    """بحث بالكود الرقمي أو النصي."""
    if not code:
        return None
    code = str(code).strip()
    obj = model.objects.filter(**{field: code}).first()
    if obj:
        return obj
    num = _numeric_value(code)
    if num:
        return model.objects.filter(**{f'{field}__icontains': str(num)}).first()
    return None


def generate_product_barcode(product):
    """
    باركود مركّب: {مجموعة}{صنف فرعي:03d}{شركة:03d}{مسلسل:04d}
    مثال: مجموعة 2 + صنف 3 + شركة 4 + مسلسل 1 → 20030040001
    """
    cat = _numeric_value(product.category.code)
    sub = _numeric_value(getattr(product, 'code', None) or product.sku) or product.pk
    co = _numeric_value(product.brand.code)
    seq = product.pk
    return f"{cat}{sub:03d}{co:03d}{seq:04d}"
