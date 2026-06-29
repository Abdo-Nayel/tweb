from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from apps.inventory.models import Product, Warehouse
from apps.inventory.services import apply_stock_movement, deduct_stock_for_sale
from apps.parties.models import Customer, Supplier
from apps.treasury.models import CashBox


class ReturnDocument(models.Model):
    class Kind(models.TextChoices):
        SALES = 'sales', 'مرتجع مبيعات'
        PURCHASE = 'purchase', 'مرتجع مشتريات'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'مسودة'
        POSTED = 'posted', 'مرحّل'

    return_number = models.CharField('رقم المرتجع', max_length=30, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    branch = models.ForeignKey(
        'pharmacy.Branch', on_delete=models.PROTECT, null=True, blank=True,
        related_name='return_documents',
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, verbose_name='المخزن')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True)
    walk_in_name = models.CharField(max_length=150, blank=True)
    walk_in_phone = models.CharField(max_length=30, blank=True)
    date = models.DateField('التاريخ')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rt_doc'
        verbose_name = 'مرتجع فاتورة'
        verbose_name_plural = 'مرتجعات الفواتير'
        ordering = ['-date', '-id']

    def __str__(self):
        return self.return_number

    @property
    def party_display(self):
        if self.kind == self.Kind.SALES:
            if self.customer_id:
                return self.customer.name
            return self.walk_in_name or 'نقدي'
        if self.supplier_id:
            return self.supplier.name
        return '—'

    def recalculate(self):
        self.subtotal = sum(line.line_total for line in self.lines.all())
        self.grand_total = self.subtotal - self.discount
        self.save(update_fields=['subtotal', 'grand_total'])

    @transaction.atomic
    def post(self, user=None):
        if self.status == self.Status.POSTED:
            return

        if self.kind == self.Kind.SALES:
            for line in self.lines.all():
                apply_stock_movement(
                    'return_in', line.product, self.warehouse, line.quantity,
                    line.unit_price, self.return_number, user=user,
                    batch_number=line.batch_number or '',
                    expiry_date=line.expiry_date,
                )
        else:
            for line in self.lines.all():
                deduct_stock_for_sale(
                    line.product, self.warehouse, line.quantity,
                    line.unit_price, self.return_number, user=user,
                )

        paid = Decimal('0')
        for pay in self.payments.all():
            paid += pay.amount
            if pay.payment_type == ReturnPayment.PayType.CASH:
                cash = CashBox.get_main()
                if self.kind == self.Kind.SALES:
                    cash.balance -= pay.amount
                else:
                    cash.balance += pay.amount
                cash.save(update_fields=['balance'])
            elif pay.bank_id:
                if self.kind == self.Kind.SALES:
                    pay.bank.balance -= pay.amount
                else:
                    pay.bank.balance += pay.amount
                pay.bank.save(update_fields=['balance'])

        self.paid_amount = paid
        credit_delta = self.grand_total - paid

        if self.kind == self.Kind.SALES and self.customer_id and credit_delta:
            self.customer.balance -= credit_delta
            self.customer.save(update_fields=['balance'])
        elif self.kind == self.Kind.PURCHASE and self.supplier_id and credit_delta:
            self.supplier.balance -= credit_delta
            self.supplier.save(update_fields=['balance'])

        self.status = self.Status.POSTED
        self.save()


class ReturnLine(models.Model):
    document = models.ForeignKey(ReturnDocument, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='الصنف')
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    batch_number = models.CharField(max_length=50, blank=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'rt_ln'
        verbose_name = 'بند مرتجع'
        verbose_name_plural = 'بنود المرتجعات'

    @property
    def line_total(self):
        return self.quantity * self.unit_price


class ReturnPayment(models.Model):
    class PayType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        BANK = 'bank', 'بنك'

    document = models.ForeignKey(ReturnDocument, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=10, choices=PayType.choices, default=PayType.CASH)
    bank = models.ForeignKey('treasury.Bank', on_delete=models.PROTECT, null=True, blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.CharField(max_length=120, blank=True)

    class Meta:
        db_table = 'rt_pay'
        verbose_name = 'سداد مرتجع'
        verbose_name_plural = 'سدادات المرتجعات'
