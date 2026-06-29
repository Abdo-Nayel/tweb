from decimal import Decimal
from django.db import models, transaction
from django.conf import settings


class Supplier(models.Model):
    """المورد"""
    code = models.CharField('الكود', max_length=20, unique=True)
    name = models.CharField('اسم المورد', max_length=150)
    phone = models.CharField('الهاتف', max_length=30, blank=True)
    address = models.CharField('العنوان', max_length=255, blank=True)
    balance = models.DecimalField('الرصيد', max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField('نشط', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pty_sup'
        verbose_name = 'مورد'
        verbose_name_plural = 'الموردين'
        ordering = ['name']

    def __str__(self):
        return self.name


class SupplierPayment(models.Model):
    """سداد مستقل لمورد — يخصم من النقدية أو البنك."""

    class PayType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        BANK = 'bank', 'بنك'

    reference = models.CharField('رقم السند', max_length=30, unique=True)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, verbose_name='المورد', related_name='payments',
    )
    date = models.DateField('التاريخ')
    amount = models.DecimalField('المبلغ', max_digits=14, decimal_places=2)
    payment_type = models.CharField('طريقة السداد', max_length=10, choices=PayType.choices, default=PayType.CASH)
    bank = models.ForeignKey(
        'treasury.Bank', on_delete=models.PROTECT, null=True, blank=True, verbose_name='البنك',
    )
    notes = models.CharField('ملاحظات', max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='supplier_payments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pty_sup_pay'
        verbose_name = 'سداد مورد'
        verbose_name_plural = 'سدادات الموردين'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.reference} — {self.supplier.name} — {self.amount}'

    @transaction.atomic
    def apply(self):
        """تطبيق السداد على رصيد المورد والخزنة/البنك."""
        from apps.treasury.models import CashBox

        self.supplier.balance -= self.amount
        self.supplier.save(update_fields=['balance'])
        if self.payment_type == self.PayType.CASH:
            cash = CashBox.get_main()
            cash.balance -= self.amount
            cash.save(update_fields=['balance'])
        elif self.bank_id:
            self.bank.balance -= self.amount
            self.bank.save(update_fields=['balance'])


class Customer(models.Model):
    """العميل"""
    code = models.CharField('الكود', max_length=20, unique=True)
    name = models.CharField('اسم العميل', max_length=150)
    phone = models.CharField('الهاتف', max_length=30, blank=True)
    address = models.CharField('العنوان', max_length=255, blank=True)
    balance = models.DecimalField('الرصيد', max_digits=14, decimal_places=2, default=0)
    credit_limit = models.DecimalField('حد الائتمان', max_digits=14, decimal_places=2, default=0)
    is_active = models.BooleanField('نشط', default=True)
    notes = models.TextField('ملاحظات', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pty_cust'
        verbose_name = 'عميل'
        verbose_name_plural = 'العملاء'
        ordering = ['name']

    def __str__(self):
        return self.name


class CustomerPayment(models.Model):
    """تحصيل مستقل من عميل — يُضاف للنقدية أو البنك."""

    class PayType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        BANK = 'bank', 'بنك'

    reference = models.CharField('رقم السند', max_length=30, unique=True)
    customer = models.ForeignKey(
        Customer, on_delete=models.PROTECT, verbose_name='العميل', related_name='payments',
    )
    date = models.DateField('التاريخ')
    amount = models.DecimalField('المبلغ', max_digits=14, decimal_places=2)
    payment_type = models.CharField('طريقة التحصيل', max_length=10, choices=PayType.choices, default=PayType.CASH)
    bank = models.ForeignKey(
        'treasury.Bank', on_delete=models.PROTECT, null=True, blank=True, verbose_name='البنك',
    )
    notes = models.CharField('ملاحظات', max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='customer_payments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'pty_cust_pay'
        verbose_name = 'تحصيل عميل'
        verbose_name_plural = 'تحصيلات العملاء'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.reference} — {self.customer.name} — {self.amount}'

    @transaction.atomic
    def apply(self):
        from apps.treasury.models import CashBox

        self.customer.balance -= self.amount
        self.customer.save(update_fields=['balance'])
        if self.payment_type == self.PayType.CASH:
            cash = CashBox.get_main()
            cash.balance += self.amount
            cash.save(update_fields=['balance'])
        elif self.bank_id:
            self.bank.balance += self.amount
            self.bank.save(update_fields=['balance'])
