from django.db import models
from django.db import transaction
from django.conf import settings


class Bank(models.Model):
    """حساب بنكي"""
    code = models.CharField('كود البنك', max_length=20, unique=True)
    name = models.CharField('اسم الحساب البنكي', max_length=120)
    account_number = models.CharField('رقم الحساب', max_length=50, blank=True)
    balance = models.DecimalField('الرصيد', max_digits=14, decimal_places=2, default=0)
    branch = models.ForeignKey(
        'pharmacy.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الفرع',
        related_name='banks',
    )
    is_active = models.BooleanField('نشط', default=True)
    notes = models.CharField('ملاحظات', max_length=255, blank=True)

    class Meta:
        verbose_name = 'بنك'
        verbose_name_plural = 'البنوك'
        ordering = ['name', 'code']

    def __str__(self):
        return f'{self.code} — {self.name}'


class ExpenseCategory(models.Model):
    code = models.CharField('الكود', max_length=20, unique=True, blank=True)
    name = models.CharField('اسم البند', max_length=120)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'بند مصروف'
        verbose_name_plural = 'بنود المصروفات'
        ordering = ['code']

    def save(self, *args, **kwargs):
        if not self.code:
            from apps.core.codes import next_serial
            self.code = next_serial(ExpenseCategory, 'code')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, verbose_name='البند', related_name='expenses')
    bank = models.ForeignKey(
        Bank,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='البنك',
        related_name='expenses',
    )
    amount = models.DecimalField('المبلغ', max_digits=14, decimal_places=2)
    date = models.DateField('التاريخ')
    description = models.CharField('الوصف', max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'مصروف'
        verbose_name_plural = 'المصروفات'
        ordering = ['-date']

    def __str__(self):
        return f'{self.category} — {self.amount}'


class CashBox(models.Model):
    """الخزنة النقدية"""
    name = models.CharField('الاسم', max_length=80, default='الخزنة الرئيسية')
    balance = models.DecimalField('الرصيد', max_digits=14, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'خزنة نقدية'
        verbose_name_plural = 'الخزائن النقدية'

    @classmethod
    def get_main(cls):
        obj, _ = cls.objects.get_or_create(pk=1, defaults={'name': 'الخزنة الرئيسية'})
        return obj

    def __str__(self):
        return f'{self.name} ({self.balance})'


class TreasuryMovement(models.Model):
    """حركة خزينة — إيداع/سحب/تحويل — جدول tr_mv"""

    class Kind(models.TextChoices):
        CASH_IN = 'cash_in', 'إيداع نقدي'
        CASH_OUT = 'cash_out', 'سحب نقدي'
        BANK_IN = 'bank_in', 'إيداع بنك'
        BANK_OUT = 'bank_out', 'سحب بنك'
        CASH_TO_BANK = 'c2b', 'تحويل نقد → بنك'
        BANK_TO_CASH = 'b2c', 'تحويل بنك → نقد'

    kind = models.CharField('النوع', max_length=10, choices=Kind.choices, db_column='k')
    bank = models.ForeignKey(
        Bank, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='البنك', related_name='movements', db_column='bank_id',
    )
    amount = models.DecimalField('المبلغ', max_digits=14, decimal_places=2, db_column='amt')
    date = models.DateField('التاريخ', db_column='dt')
    notes = models.CharField('ملاحظات', max_length=255, blank=True, db_column='nt')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='treasury_movements', db_column='uid',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='crt')

    class Meta:
        db_table = 'tr_mv'
        verbose_name = 'حركة خزينة'
        verbose_name_plural = 'حركات الخزينة'
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.get_kind_display()} — {self.amount}'

    @transaction.atomic
    def apply(self):
        cash = CashBox.get_main()
        amt = self.amount
        if self.kind == self.Kind.CASH_IN:
            cash.balance += amt
            cash.save(update_fields=['balance'])
        elif self.kind == self.Kind.CASH_OUT:
            if cash.balance < amt:
                raise ValueError('رصيد الخزنة غير كافٍ')
            cash.balance -= amt
            cash.save(update_fields=['balance'])
        elif self.kind in (self.Kind.BANK_IN, self.Kind.BANK_OUT):
            if not self.bank_id:
                raise ValueError('اختر البنك')
            if self.kind == self.Kind.BANK_IN:
                self.bank.balance += amt
            else:
                if self.bank.balance < amt:
                    raise ValueError('رصيد البنك غير كافٍ')
                self.bank.balance -= amt
            self.bank.save(update_fields=['balance'])
        elif self.kind == self.Kind.CASH_TO_BANK:
            if not self.bank_id:
                raise ValueError('اختر البنك')
            if cash.balance < amt:
                raise ValueError('رصيد الخزنة غير كافٍ')
            cash.balance -= amt
            self.bank.balance += amt
            cash.save(update_fields=['balance'])
            self.bank.save(update_fields=['balance'])
        elif self.kind == self.Kind.BANK_TO_CASH:
            if not self.bank_id:
                raise ValueError('اختر البنك')
            if self.bank.balance < amt:
                raise ValueError('رصيد البنك غير كافٍ')
            self.bank.balance -= amt
            cash.balance += amt
            self.bank.save(update_fields=['balance'])
            cash.save(update_fields=['balance'])
