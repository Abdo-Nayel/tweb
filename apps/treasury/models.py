from django.db import models
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
