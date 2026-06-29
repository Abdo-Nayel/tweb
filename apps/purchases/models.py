from decimal import Decimal
from django.db import models, transaction
from django.conf import settings

from apps.parties.models import Supplier
from apps.inventory.models import Product, Warehouse
from apps.inventory.services import apply_stock_movement


class PurchaseInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'مسودة'
        POSTED = 'posted', 'مرحّلة'

    invoice_number = models.CharField('رقم الفاتورة', max_length=30, unique=True)
    document_number = models.CharField('رقم المستند', max_length=30, blank=True, default='')
    currency = models.CharField('العملة', max_length=10, default='ج.م')
    branch = models.ForeignKey(
        'pharmacy.Branch', on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='الفرع', related_name='purchase_invoices',
    )
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, verbose_name='المورد')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name='المخزن')
    date = models.DateField('التاريخ')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField('خصم إجمالي', max_digits=14, decimal_places=2, default=0)
    tax = models.DecimalField('ضريبة إجمالية', max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField('الإجمالي', max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField('المدفوع', max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pu_inv'
        verbose_name = 'فاتورة مشتريات'
        verbose_name_plural = 'فواتير المشتريات'
        ordering = ['-date', '-id']

    def __str__(self):
        return self.invoice_number

    def recalculate(self):
        lines = self.lines.all()
        self.subtotal = sum(l.line_total for l in lines)
        self.grand_total = self.subtotal - self.discount + self.tax
        self.save()

    @transaction.atomic
    def post(self, user=None):
        if self.status == self.Status.POSTED:
            return
        for line in self.lines.all():
            apply_stock_movement(
                'purchase', line.product, self.warehouse, line.quantity,
                line.unit_cost, self.invoice_number, user=user,
                batch_number=line.batch_number or '',
                expiry_date=line.expiry_date,
            )
            line.product.cost_price = line.unit_cost
            if line.sale_price:
                line.product.sale_price = line.sale_price
            line.product.save(update_fields=['cost_price', 'sale_price'])

        from apps.treasury.models import CashBox
        paid = Decimal('0')
        for pay in self.payments.all():
            paid += pay.amount
            if pay.payment_type == PurchasePayment.PayType.CASH:
                cash = CashBox.get_main()
                cash.balance -= pay.amount
                cash.save(update_fields=['balance'])
            elif pay.bank_id:
                pay.bank.balance -= pay.amount
                pay.bank.save(update_fields=['balance'])

        self.paid_amount = paid
        self.supplier.balance += self.grand_total - paid
        self.supplier.save(update_fields=['balance'])
        self.status = self.Status.POSTED
        self.save()


class PurchaseLine(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='الصنف')
    quantity = models.DecimalField('الكمية', max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField('سعر الشراء', max_digits=12, decimal_places=2)
    sale_price = models.DecimalField('سعر البيع', max_digits=12, decimal_places=2, default=0)
    discount_percent = models.DecimalField('نسبة الخصم %', max_digits=6, decimal_places=2, default=0)
    discount = models.DecimalField('خصم', max_digits=12, decimal_places=2, default=0)
    line_tax = models.DecimalField('ضريبة', max_digits=12, decimal_places=2, default=0)
    shipping_cost = models.DecimalField('تكلفة شحن/قطعة', max_digits=12, decimal_places=2, default=0)
    batch_number = models.CharField('رقم التشغيلة', max_length=50, blank=True)
    expiry_date = models.DateField('تاريخ الصلاحية', null=True, blank=True)

    class Meta:
        db_table = 'pu_ln'
        verbose_name = 'بند مشتريات'
        verbose_name_plural = 'بنود المشتريات'

    @property
    def line_gross(self):
        return self.quantity * self.unit_cost

    @property
    def line_total(self):
        disc = self.discount
        if self.discount_percent:
            disc = self.line_gross * self.discount_percent / Decimal('100')
        return self.line_gross - disc + self.line_tax + (self.shipping_cost * self.quantity)


class PurchasePayment(models.Model):
    class PayType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        BANK = 'bank', 'بنك'

    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=10, choices=PayType.choices, default=PayType.CASH)
    bank = models.ForeignKey(
        'treasury.Bank', on_delete=models.PROTECT, null=True, blank=True, verbose_name='البنك',
    )
    amount = models.DecimalField('المبلغ', max_digits=14, decimal_places=2)
    notes = models.CharField('ملاحظات', max_length=120, blank=True)

    class Meta:
        db_table = 'pu_pay'
        verbose_name = 'سداد مشتريات'
        verbose_name_plural = 'سدادات المشتريات'

    def __str__(self):
        return f'{self.get_payment_type_display()} {self.amount}'
