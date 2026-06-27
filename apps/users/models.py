from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'مدير'
        PHARMACIST = 'pharmacist', 'صيدلي'
        CASHIER = 'cashier', 'كاشير'
        ACCOUNTANT = 'accountant', 'محاسب'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CASHIER)
    code = models.CharField('الكود', max_length=20, unique=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    branch = models.ForeignKey(
        'pharmacy.Branch',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الفرع',
        related_name='users',
    )
    dashboard_shortcuts = models.JSONField(
        'اختصارات لوحة التحكم',
        blank=True,
        default=list,
    )

    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        if not self.code:
            from apps.core.codes import next_serial
            self.code = next_serial(User, 'code')
        super().save(*args, **kwargs)


class UserModuleAccess(models.Model):
    class Module(models.TextChoices):
        DASHBOARD = 'dashboard', 'لوحة التحكم'
        WAREHOUSES = 'warehouses', 'المخازن'
        CATEGORIES = 'categories', 'الأصناف الرئيسية'
        COMPANIES = 'companies', 'الشركات المنتجة'
        PRODUCTS = 'products', 'الأصناف الفرعية'
        STOCK = 'stock', 'المخزون والأرصدة'
        SUPPLIERS = 'suppliers', 'الموردين'
        CUSTOMERS = 'customers', 'العملاء'
        PURCHASES = 'purchases', 'المشتريات'
        SALES = 'sales', 'المبيعات'
        EXPENSES = 'expenses', 'المصروفات'
        DAILY_REPORT = 'daily_report', 'تقرير يومي'
        ACTIVITY_LOG = 'activity_log', 'سجل الحركات'
        SETTINGS = 'settings', 'الإعدادات'

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_access')
    module = models.CharField(max_length=20, choices=Module.choices)
    can_view = models.BooleanField('عرض', default=True)
    can_add = models.BooleanField('إضافة', default=False)
    can_edit = models.BooleanField('تعديل', default=False)
    can_delete = models.BooleanField('حذف', default=False)

    class Meta:
        verbose_name = 'صلاحية مستخدم'
        verbose_name_plural = 'صلاحيات المستخدمين'
        unique_together = [['user', 'module']]

    def __str__(self):
        return f'{self.user.username} — {self.get_module_display()}'
