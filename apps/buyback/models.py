from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models, transaction

from apps.inventory.models import Product, Warehouse
from apps.inventory.services import apply_stock_movement
from apps.treasury.models import Bank, CashBox


class ExternalBuyback(models.Model):
    """شراء جهاز من عميل خارجي — جدول bb_doc"""

    class Status(models.TextChoices):
        DRAFT = 'draft', 'مسودة'
        POSTED = 'posted', 'مرحّل'

    class PayType(models.TextChoices):
        CASH = 'cash', 'نقدي'
        BANK = 'bank', 'بنك'

    doc_no = models.CharField('رقم المستند', max_length=20, unique=True, db_column='no')
    date = models.DateField('التاريخ', db_column='dt')
    branch = models.ForeignKey(
        'pharmacy.Branch', on_delete=models.PROTECT, null=True, blank=True,
        related_name='buybacks', db_column='br_id',
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, verbose_name='المخزن',
        related_name='buybacks', db_column='wh_id',
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, verbose_name='الصنف',
        related_name='buybacks', db_column='prod_id',
    )
    seller_name = models.CharField('اسم البائع', max_length=120, db_column='seller_nm')
    seller_phone = models.CharField('التليفون', max_length=30, db_column='seller_ph')
    national_id = models.CharField('رقم البطاقة', max_length=20, db_column='nid')
    serial_number = models.CharField('السيريال / IMEI', max_length=50, db_column='serial')
    device_specs = models.TextField('مواصفات الجهاز', db_column='specs')
    model_name = models.CharField('الموديل', max_length=120, blank=True, db_column='model')
    storage = models.CharField('السعة', max_length=40, blank=True, db_column='stor')
    color = models.CharField('اللون', max_length=40, blank=True, db_column='clr')
    purchase_amount = models.DecimalField('مبلغ الشراء', max_digits=14, decimal_places=2, db_column='amt')
    sale_price = models.DecimalField('سعر البيع المقترح', max_digits=14, decimal_places=2, default=0, db_column='sale')
    payment_type = models.CharField(max_length=10, choices=PayType.choices, default=PayType.CASH, db_column='pay_typ')
    bank = models.ForeignKey(
        Bank, on_delete=models.PROTECT, null=True, blank=True,
        verbose_name='البنك', db_column='bank_id',
    )
    id_card_photo = models.ImageField('صورة البطاقة', upload_to='buyback/ids/', blank=True, null=True, db_column='id_img')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_column='st')
    notes = models.TextField('ملاحظات', blank=True, db_column='nt')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='buybacks', db_column='uid',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_column='crt')

    class Meta:
        db_table = 'bb_doc'
        verbose_name = 'شراء من فرد'
        verbose_name_plural = 'مشتريات من أفراد'
        ordering = ['-date', '-id']

    def __str__(self):
        return self.doc_no

    @property
    def device_label(self):
        parts = [self.product.name]
        if self.model_name:
            parts.append(self.model_name)
        if self.storage:
            parts.append(self.storage)
        if self.color:
            parts.append(self.color)
        return ' — '.join(parts)

    @transaction.atomic
    def post(self, user=None):
        if self.status == self.Status.POSTED:
            return

        if self.payment_type == self.PayType.BANK and not self.bank_id:
            raise ValueError('اختر البنك للدفع')

        from apps.inventory.models import StockLot
        if self.serial_number and StockLot.objects.filter(
            serial_number=self.serial_number, quantity__gt=0,
        ).exists():
            raise ValueError(f'السيريال {self.serial_number} مسجّل مسبقاً في المخزون')

        apply_stock_movement(
            'purchase', self.product, self.warehouse, Decimal('1'),
            self.purchase_amount, self.doc_no,
            notes=f'شراء من فرد: {self.seller_name}',
            user=user,
            serial_number=self.serial_number,
        )

        self.product.cost_price = self.purchase_amount
        self.product.condition = Product.Condition.USED
        update_fields = ['cost_price', 'condition']
        if self.sale_price > 0:
            self.product.sale_price = self.sale_price
            update_fields.append('sale_price')
        if self.model_name and not self.product.model_name:
            self.product.model_name = self.model_name
            update_fields.append('model_name')
        if self.storage and not self.product.storage:
            self.product.storage = self.storage
            update_fields.append('storage')
        if self.color and not self.product.color:
            self.product.color = self.color
            update_fields.append('color')
        self.product.save(update_fields=update_fields)

        amt = self.purchase_amount
        if self.payment_type == self.PayType.CASH:
            cash = CashBox.get_main()
            if cash.balance < amt:
                raise ValueError('رصيد الخزنة غير كافٍ')
            cash.balance -= amt
            cash.save(update_fields=['balance'])
        else:
            if self.bank.balance < amt:
                raise ValueError('رصيد البنك غير كافٍ')
            self.bank.balance -= amt
            self.bank.save(update_fields=['balance'])

        self.status = self.Status.POSTED
        self.save(update_fields=['status'])
