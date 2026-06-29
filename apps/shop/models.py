from django.conf import settings
from django.db import models


class ShopProfile(models.Model):
    """بيانات المحل الأساسية"""
    name = models.CharField('اسم المحل', max_length=200)
    owner_name = models.CharField('اسم المالك', max_length=120, blank=True)
    phone = models.CharField('الهاتف', max_length=30, blank=True)
    address = models.CharField('العنوان', max_length=255, blank=True)
    tax_number = models.CharField('الرقم الضريبي', max_length=50, blank=True)
    logo = models.ImageField('الشعار', upload_to='logos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'بيانات المحل'
        verbose_name_plural = 'بيانات المحل'
        db_table = 'shop_prf'

    def __str__(self):
        return self.name


PharmacyProfile = ShopProfile


class Branch(models.Model):
    """فرع المحل"""
    code = models.CharField('كود الفرع', max_length=20, unique=True)
    name = models.CharField('اسم الفرع', max_length=120)
    address = models.CharField('العنوان', max_length=255, blank=True)
    phone = models.CharField('الهاتف', max_length=30, blank=True)
    is_active = models.BooleanField('نشط', default=True)

    class Meta:
        db_table = 'shop_br'
        verbose_name = 'فرع'
        verbose_name_plural = 'الفروع'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} — {self.name}'


class BarcodeLabelSettings(models.Model):
    """إعدادات طباعة ليبل الباركود"""

    class CodeType(models.TextChoices):
        BARCODE = 'barcode', 'باركود (CODE128)'
        QR = 'qr', 'QR Code'

    label_width_mm = models.PositiveIntegerField('عرض الليبل (مم)', default=50)
    label_height_mm = models.PositiveIntegerField('ارتفاع الليبل (مم)', default=30)
    code_type = models.CharField(
        'نوع الكود', max_length=10, choices=CodeType.choices, default=CodeType.BARCODE,
    )
    show_product_name = models.BooleanField('إظهار اسم المنتج', default=True)
    show_sku = models.BooleanField('إظهار كود الصنف', default=True)
    show_price = models.BooleanField('إظهار السعر', default=True)
    show_company = models.BooleanField('إظهار الماركة', default=False)
    font_size = models.PositiveIntegerField('حجم الخط', default=10)
    barcode_height = models.PositiveIntegerField('ارتفاع الباركود', default=40)
    copies_default = models.PositiveIntegerField('عدد النسخ الافتراضي', default=1)

    class Meta:
        db_table = 'lbl_cfg'
        verbose_name = 'إعدادات ليبل الباركود'
        verbose_name_plural = 'إعدادات ليبل الباركود'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'إعدادات ليبل الباركود'


class ReceiptSettings(models.Model):
    """إعدادات طباعة إيصال البيع — Xprinter 80mm"""
    header_text = models.TextField('نص الهيدر', blank=True, default='شكراً لزيارتكم')
    footer_text = models.TextField('نص الفوتر', blank=True, default='نتمنى لكم تجربة ممتعة')
    receipt_logo = models.ImageField('لوجو الإيصال', upload_to='receipts/', blank=True, null=True)
    use_shop_logo = models.BooleanField(
        'استخدام شعار المحل', default=True, db_column='use_pharmacy_logo',
    )
    show_logo = models.BooleanField('إظهار اللوجو', default=True)
    paper_width_mm = models.PositiveIntegerField('عرض الورق (مم)', default=80)
    title_font_size = models.PositiveIntegerField('حجم خط العنوان', default=15)
    body_font_size = models.PositiveIntegerField('حجم خط المحتوى', default=12)
    show_cashier = models.BooleanField('إظهار الكاشير', default=True)
    show_customer = models.BooleanField('إظهار بيانات العميل', default=True)
    show_discount = models.BooleanField('إظهار الخصم', default=True)
    auto_print = models.BooleanField('طباعة تلقائية بعد الترحيل', default=False)

    class Meta:
        db_table = 'rcp_cfg'
        verbose_name = 'إعدادات إيصال البيع'
        verbose_name_plural = 'إعدادات إيصال البيع'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'إعدادات إيصال البيع'


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', 'تسجيل دخول'
        LOGOUT = 'logout', 'تسجيل خروج'
        CREATE = 'create', 'إضافة'
        UPDATE = 'update', 'تعديل'
        DELETE = 'delete', 'حذف'
        POST = 'post', 'ترحيل'
        EXPORT = 'export', 'تصدير'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    username = models.CharField('المستخدم', max_length=150)
    log_no = models.CharField('رقم الحركة', max_length=20, unique=True, db_column='no', blank=True)
    action = models.CharField('العملية', max_length=20, choices=Action.choices)
    section = models.CharField('القسم', max_length=80, blank=True)
    description = models.TextField('التفاصيل', blank=True)
    object_ref = models.CharField('المرجع', max_length=120, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    branch = models.ForeignKey(
        'pharmacy.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    created_at = models.DateTimeField('الوقت', auto_now_add=True)

    class Meta:
        db_table = 'act_log'
        verbose_name = 'سجل حركة'
        verbose_name_plural = 'سجل الحركات'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.log_no or self.pk} — {self.username} — {self.get_action_display()}'

    def save(self, *args, **kwargs):
        if not self.log_no:
            from apps.core.codes import next_serial
            self.log_no = next_serial(ActivityLog, 'log_no')
        super().save(*args, **kwargs)


class TelegramSettings(models.Model):
    """إعدادات بوت تليجرام للإشعارات"""

    bot_token = models.CharField('Bot Token', max_length=120, blank=True)
    chat_id = models.CharField('Chat ID', max_length=40, blank=True)
    enabled = models.BooleanField('تفعيل الإشعارات', default=False)
    notify_on_login = models.BooleanField('إشعار تسجيل الدخول', default=True)

    class Meta:
        verbose_name = 'إعدادات تليجرام'
        verbose_name_plural = 'إعدادات تليجرام'
        db_table = 'tg_cfg'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return 'إعدادات تليجرام'
