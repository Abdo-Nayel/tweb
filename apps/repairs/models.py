from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from apps.inventory.models import Product, Warehouse
from apps.inventory.services import apply_stock_movement
from apps.treasury.models import Bank, CashBox


class RepairOrder(models.Model):
    """أمر صيانة — جدول مختصر rep_ord"""

    class Status(models.TextChoices):
        OPEN = 'open', 'مستلم'
        WORKING = 'working', 'جاري العمل'
        READY = 'ready', 'جاهز للاستلام'
        DONE = 'done', 'مكتمل'
        CANCEL = 'cancel', 'ملغي'

    order_no = models.CharField('رقم الأمر', max_length=20, unique=True, db_column='no')
    date = models.DateField('التاريخ', db_column='dt')
    customer_name = models.CharField('اسم العميل', max_length=120, db_column='cust_nm')
    customer_phone = models.CharField('التليفون', max_length=30, db_column='cust_ph')
    device_desc = models.CharField('الجهاز', max_length=200, db_column='dev')
    problem = models.TextField('العطل', blank=True, db_column='prob')
    labor_fee = models.DecimalField('أجر الصيانة', max_digits=12, decimal_places=2, default=0, db_column='labor')
    parts_cost = models.DecimalField('تكلفة قطع الغيار', max_digits=12, decimal_places=2, default=0, db_column='parts')
    total = models.DecimalField('الإجمالي', max_digits=14, decimal_places=2, default=0, db_column='tot')
    deposit = models.DecimalField('العربون', max_digits=14, decimal_places=2, default=0, db_column='dep')
    paid = models.DecimalField('المدفوع', max_digits=14, decimal_places=2, default=0, db_column='paid')
    status = models.CharField('الحالة', max_length=10, choices=Status.choices, default=Status.OPEN, db_column='st')
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, verbose_name='المخزن',
        related_name='repair_orders', db_column='wh_id',
    )
    notes = models.TextField('ملاحظات', blank=True, db_column='nt')
    stock_deducted = models.BooleanField('تم خصم المخزون', default=False, db_column='stk_ok')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='repair_orders', db_column='uid',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='crt')
    completed_at = models.DateTimeField(null=True, blank=True, db_column='done_at')

    class Meta:
        db_table = 'rep_ord'
        verbose_name = 'أمر صيانة'
        verbose_name_plural = 'أوامر الصيانة'
        ordering = ['-date', '-id']

    def __str__(self):
        return self.order_no

    @property
    def remaining(self):
        return max(self.total - self.paid, Decimal('0'))

    def recalculate(self):
        parts = sum(p.line_cost for p in self.part_lines.all())
        self.parts_cost = parts
        self.total = parts + self.labor_fee
        self.save(update_fields=['parts_cost', 'total'])

    @transaction.atomic
    def deduct_stock_parts(self, user=None):
        if self.stock_deducted:
            return
        for part in self.part_lines.filter(source=RepairPart.Source.STOCK, product_id__isnull=False):
            apply_stock_movement(
                'adjust_out', part.product, self.warehouse, part.quantity,
                part.unit_cost, self.order_no, user=user,
            )
        self.stock_deducted = True
        self.save(update_fields=['stock_deducted'])

    @transaction.atomic
    def record_payment(self, amount, pay_type='cash', bank=None, is_deposit=False, user=None):
        amt = Decimal(str(amount))
        if amt <= 0:
            return
        RepairPayment.objects.create(
            order=self, amount=amt, payment_type=pay_type, bank=bank,
            is_deposit=is_deposit, created_by=user,
        )
        if pay_type == RepairPayment.PayType.CASH:
            cash = CashBox.get_main()
            cash.balance += amt
            cash.save(update_fields=['balance'])
        elif bank:
            bank.balance += amt
            bank.save(update_fields=['balance'])
        self.paid += amt
        if is_deposit:
            self.deposit += amt
        self.save(update_fields=['paid', 'deposit'])


class RepairPart(models.Model):
    """قطعة غيار — جدول rep_prt"""

    class Source(models.TextChoices):
        STOCK = 'stock', 'من المخزون'
        EXTERNAL = 'external', 'مورد خارجي'

    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='part_lines', db_column='ord_id')
    source = models.CharField('المصدر', max_length=10, choices=Source.choices, db_column='src')
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='المنتج', db_column='prod_id',
    )
    ext_desc = models.CharField('بيان خارجي', max_length=255, blank=True, db_column='ext_desc')
    quantity = models.DecimalField('الكمية', max_digits=10, decimal_places=2, default=1, db_column='qty')
    unit_cost = models.DecimalField('التكلفة', max_digits=12, decimal_places=2, default=0, db_column='cost')

    class Meta:
        db_table = 'rep_prt'
        verbose_name = 'قطعة صيانة'
        verbose_name_plural = 'قطع الصيانة'

    @property
    def line_cost(self):
        return self.quantity * self.unit_cost

    def __str__(self):
        if self.product_id:
            return str(self.product)
        return self.ext_desc or '—'


class RepairPayment(models.Model):
    """دفعة صيانة — جدول rep_pay"""

    class PayType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        BANK = 'bank', 'بنك'

    order = models.ForeignKey(RepairOrder, on_delete=models.CASCADE, related_name='payments', db_column='ord_id')
    payment_type = models.CharField(max_length=10, choices=PayType.choices, default=PayType.CASH, db_column='typ')
    bank = models.ForeignKey(Bank, on_delete=models.PROTECT, null=True, blank=True, db_column='bank_id')
    amount = models.DecimalField(max_digits=14, decimal_places=2, db_column='amt')
    is_deposit = models.BooleanField('عربون', default=False, db_column='is_dep')
    notes = models.CharField(max_length=120, blank=True, db_column='nt')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, db_column='uid',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='crt')

    class Meta:
        db_table = 'rep_pay'
        verbose_name = 'دفعة صيانة'
        verbose_name_plural = 'دفعات الصيانة'
        ordering = ['created_at']
