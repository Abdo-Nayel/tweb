from decimal import Decimal
from django.db import models, transaction
from django.conf import settings

from apps.parties.models import Customer
from apps.inventory.models import Product, Warehouse
from apps.inventory.services import deduct_stock_for_sale, restore_stock_from_sale


class SalesInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'مسودة'
        POSTED = 'posted', 'مرحّلة'

    class PaymentType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        CREDIT = 'credit', 'آجل'

    invoice_number = models.CharField('رقم الفاتورة', max_length=30, unique=True)
    branch = models.ForeignKey(
        'pharmacy.Branch', on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='الفرع', related_name='sales_invoices',
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, verbose_name='العميل', null=True, blank=True,
    )
    walk_in_name = models.CharField('اسم العميل النقدي', max_length=150, blank=True)
    walk_in_phone = models.CharField('موبايل العميل النقدي', max_length=30, blank=True)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name='المخزن')
    date = models.DateField('التاريخ')
    payment_type = models.CharField(max_length=10, choices=PaymentType.choices, default=PaymentType.CASH)
    currency = models.CharField('العملة', max_length=10, default='ج.م')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField('الخصم', max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField('الإجمالي', max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField('المدفوع', max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sl_inv'
        verbose_name = 'فاتورة مبيعات'
        verbose_name_plural = 'فواتير المبيعات'
        ordering = ['-date', '-id']

    def __str__(self):
        return self.invoice_number

    @property
    def buyer_display(self):
        if self.payment_type == self.PaymentType.CREDIT and self.customer_id:
            return self.customer.name
        return 'نقدي'

    @property
    def ledger_label(self):
        if self.payment_type == self.PaymentType.CREDIT and self.customer_id:
            return self.customer.name
        return 'نقدي'

    @property
    def receipt_buyer_display(self):
        if self.customer_id:
            return self.customer.name
        if self.walk_in_name:
            return self.walk_in_name + (f' ({self.walk_in_phone})' if self.walk_in_phone else '')
        return 'نقدي'

    def recalculate(self):
        lines = self.lines.all()
        self.subtotal = sum(l.line_total for l in lines)
        self.grand_total = self.subtotal - self.discount
        self.save()

    @property
    def total_cost(self):
        total = Decimal('0')
        for line in self.lines.all():
            total += line.line_cost
        return total

    @property
    def gross_profit(self):
        return self.grand_total - self.total_cost

    @transaction.atomic
    def post(self, user=None):
        if self.status == self.Status.POSTED:
            return
        for line in self.lines.all():
            cost = line.unit_cost or line.product.cost_price
            if not line.unit_cost:
                line.unit_cost = cost
                line.save(update_fields=['unit_cost'])
            deduct_stock_for_sale(
                line.product, self.warehouse, line.quantity,
                cost, self.invoice_number, user=user,
            )

        from apps.treasury.models import CashBox
        paid = Decimal('0')
        for pay in self.payments.all():
            paid += pay.amount
            if pay.payment_type == SalesPayment.PayType.CASH:
                cash = CashBox.get_main()
                cash.balance += pay.amount
                cash.save(update_fields=['balance'])
            elif pay.bank_id:
                pay.bank.balance += pay.amount
                pay.bank.save(update_fields=['balance'])

        self.paid_amount = paid
        if self.payment_type == self.PaymentType.CREDIT and self.customer_id:
            self.customer.balance += self.grand_total - paid
            self.customer.save(update_fields=['balance'])

        self.status = self.Status.POSTED
        self.save()

    @transaction.atomic
    def unpost(self, user=None):
        """إلغاء ترحيل الفاتورة لفتحها للتعديل أو الحذف."""
        if self.status != self.Status.POSTED:
            return

        from apps.treasury.models import CashBox

        for pay in self.payments.all():
            if pay.payment_type == SalesPayment.PayType.CASH:
                cash = CashBox.get_main()
                cash.balance -= pay.amount
                cash.save(update_fields=['balance'])
            elif pay.bank_id:
                pay.bank.balance -= pay.amount
                pay.bank.save(update_fields=['balance'])

        if self.payment_type == self.PaymentType.CREDIT and self.customer_id:
            self.customer.balance -= self.grand_total - self.paid_amount
            self.customer.save(update_fields=['balance'])

        restore_stock_from_sale(self.invoice_number, user=user)
        self.status = self.Status.DRAFT
        self.save(update_fields=['status'])


class SalesLine(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='الصنف')
    quantity = models.DecimalField('الكمية', max_digits=12, decimal_places=2)
    unit_price = models.DecimalField('سعر البيع', max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField('تكلفة الوحدة', max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField('خصم', max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'sl_ln'
        verbose_name = 'بند مبيعات'
        verbose_name_plural = 'بنود المبيعات'

    @property
    def line_total(self):
        return self.quantity * self.unit_price - self.discount

    @property
    def line_cost(self):
        return self.quantity * (self.unit_cost or self.product.cost_price)

    @property
    def line_profit(self):
        return self.line_total - self.line_cost


class SalesPayment(models.Model):
    class PayType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        BANK = 'bank', 'بنك'

    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=10, choices=PayType.choices, default=PayType.CASH)
    bank = models.ForeignKey(
        'treasury.Bank', on_delete=models.PROTECT, null=True, blank=True, verbose_name='البنك',
    )
    amount = models.DecimalField('المبلغ', max_digits=14, decimal_places=2)
    notes = models.CharField('ملاحظات', max_length=120, blank=True)

    class Meta:
        db_table = 'sl_pay'
        verbose_name = 'تحصيل فاتورة مبيعات'
        verbose_name_plural = 'تحصيلات فواتير المبيعات'

    def __str__(self):
        return f'{self.get_payment_type_display()} {self.amount}'
