from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.conf import settings


class Warehouse(models.Model):
    """المخزن"""
    code = models.CharField('الكود', max_length=20, unique=True)
    name = models.CharField('اسم المخزن', max_length=120)
    branch = models.ForeignKey(
        'pharmacy.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الفرع',
        related_name='warehouses',
    )
    location = models.CharField('الموقع', max_length=200, blank=True)
    is_active = models.BooleanField('نشط', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مخزن'
        verbose_name_plural = 'المخازن'
        ordering = ['code']

    def __str__(self):
        return f'{self.code} - {self.name}'


class ProductCategory(models.Model):
    """فئة المنتج — هواتف / إكسسوارات / قطع غيار"""
    code = models.CharField('الكود', max_length=20, unique=True)
    name = models.CharField('اسم الفئة', max_length=150)
    description = models.TextField('الوصف', blank=True)
    is_active = models.BooleanField('نشط', default=True)

    class Meta:
        verbose_name = 'فئة منتج'
        verbose_name_plural = 'فئات المنتجات'
        ordering = ['code']
        db_table = 'inventory_drugcategory'

    def __str__(self):
        return self.name


DrugCategory = ProductCategory


class Brand(models.Model):
    """الماركة — Apple, Samsung, Xiaomi..."""
    code = models.CharField('الكود', max_length=20, unique=True)
    name = models.CharField('اسم الماركة', max_length=150)
    country = models.CharField('بلد المنشأ', max_length=80, blank=True)
    phone = models.CharField('الهاتف', max_length=30, blank=True)
    is_active = models.BooleanField('نشط', default=True)

    class Meta:
        verbose_name = 'ماركة'
        verbose_name_plural = 'الماركات'
        ordering = ['name']
        db_table = 'inventory_drugcompany'

    def __str__(self):
        return self.name


DrugCompany = Brand


class Product(models.Model):
    """المنتج — جهاز / إكسسوار"""
    class Unit(models.TextChoices):
        PIECE = 'piece', 'قطعة'
        SET = 'set', 'طقم'
        BOX = 'box', 'علبة'

    class Condition(models.TextChoices):
        NEW = 'new', 'جديد'
        USED = 'used', 'مستعمل'
        REFURB = 'refurb', 'مجدّد'
        OPEN_BOX = 'open_box', 'مفتوح العبوة'

    sku = models.CharField('كود الصنف', max_length=30, unique=True)
    name = models.CharField('اسم المنتج', max_length=200)
    category = models.ForeignKey(
        ProductCategory, on_delete=models.PROTECT,
        verbose_name='الفئة', related_name='products',
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.PROTECT,
        verbose_name='الماركة', related_name='products',
    )
    model_name = models.CharField('الموديل', max_length=120, blank=True)
    storage = models.CharField('السعة / الذاكرة', max_length=40, blank=True)
    color = models.CharField('اللون', max_length=40, blank=True)
    condition = models.CharField(
        'الحالة', max_length=10,
        choices=Condition.choices, default=Condition.NEW,
    )
    is_serialized = models.BooleanField('تتبع بالسيريال/IMEI', default=True)
    unit = models.CharField('الوحدة', max_length=10, choices=Unit.choices, default=Unit.PIECE)
    barcode = models.CharField('الباركود', max_length=50, blank=True)
    cost_price = models.DecimalField('تكلفة الشراء', max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField('سعر البيع', max_digits=12, decimal_places=2, default=0)
    min_stock = models.DecimalField('حد الطلب', max_digits=12, decimal_places=2, default=0)
    max_stock = models.DecimalField('الحد الأقصى', max_digits=12, decimal_places=2, default=0)
    warranty_months = models.PositiveIntegerField('ضمان (شهر)', default=12)
    is_active = models.BooleanField('نشط', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='products_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'منتج'
        verbose_name_plural = 'المنتجات'
        ordering = ['name']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new or not self.barcode:
            from apps.core.codes import generate_product_barcode
            new_barcode = generate_product_barcode(self)
            if self.barcode != new_barcode:
                self.barcode = new_barcode
                super().save(update_fields=['barcode'])

    def __str__(self):
        return f'{self.sku} - {self.name}'

    @property
    def company(self):
        """Alias for legacy code referencing company."""
        return self.brand

    @company.setter
    def company(self, value):
        self.brand = value

    @property
    def total_quantity(self):
        return self.stock_lots.aggregate(t=Sum('quantity'))['t'] or Decimal('0')

    @property
    def stock_value(self):
        return self.total_quantity * self.cost_price

    @property
    def is_low_stock(self):
        return self.total_quantity <= self.min_stock


class StockLot(models.Model):
    """رصيد المنتج في مخزن — مع سيريال/IMEI للأجهزة"""
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name='stock_lots', verbose_name='المنتج',
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.CASCADE,
        related_name='stock_lots', verbose_name='المخزن',
    )
    quantity = models.DecimalField('الكمية', max_digits=12, decimal_places=2, default=1)
    serial_number = models.CharField(
        'السيريال / IMEI', max_length=50, blank=True, db_column='batch_number',
    )
    warranty_start = models.DateField('بداية الضمان', null=True, blank=True)
    warranty_end = models.DateField(
        'نهاية الضمان', null=True, blank=True, db_column='expiry_date',
    )

    class Meta:
        verbose_name = 'رصيد مخزن'
        verbose_name_plural = 'أرصدة المخازن'
        unique_together = [['product', 'warehouse', 'serial_number']]

    def __str__(self):
        serial = f' [{self.serial_number}]' if self.serial_number else ''
        return f'{self.product.name} @ {self.warehouse.name}: {self.quantity}{serial}'

    @property
    def batch_number(self):
        return self.serial_number

    @batch_number.setter
    def batch_number(self, value):
        self.serial_number = value

    @property
    def expiry_date(self):
        return self.warranty_end

    @expiry_date.setter
    def expiry_date(self, value):
        self.warranty_end = value

    @property
    def days_to_warranty_end(self):
        if not self.warranty_end:
            return None
        from datetime import date
        return (self.warranty_end - date.today()).days

    days_to_expiry = days_to_warranty_end


class StockMovement(models.Model):
    """حركة مخزنية — تسوية / تحويل / رصيد افتتاحي"""
    class MoveType(models.TextChoices):
        OPENING = 'opening', 'رصيد افتتاحي'
        PURCHASE = 'purchase', 'مشتريات'
        SALE = 'sale', 'مبيعات'
        TRANSFER = 'transfer', 'تحويل'
        ADJUST_IN = 'adjust_in', 'تسوية إضافة'
        ADJUST_OUT = 'adjust_out', 'تسوية خصم'
        RETURN_IN = 'return_in', 'مرتجع شراء'
        RETURN_OUT = 'return_out', 'مرتجع بيع'

    move_type = models.CharField('نوع الحركة', max_length=15, choices=MoveType.choices)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='المنتج')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name='المخزن')
    quantity = models.DecimalField('الكمية', max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=12, decimal_places=2, default=0)
    reference = models.CharField('مرجع', max_length=50, blank=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'حركة مخزنية'
        verbose_name_plural = 'الحركات المخزنية'
        ordering = ['-created_at']
