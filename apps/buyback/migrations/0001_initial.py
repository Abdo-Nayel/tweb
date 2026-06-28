# Generated manually

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0004_phone_shop_transform'),
        ('pharmacy', '0007_features_pos_repairs_tg'),
        ('treasury', '0007_treasury_movement'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalBuyback',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('doc_no', models.CharField(db_column='no', max_length=20, unique=True, verbose_name='رقم المستند')),
                ('date', models.DateField(db_column='dt', verbose_name='التاريخ')),
                ('seller_name', models.CharField(db_column='seller_nm', max_length=120, verbose_name='اسم البائع')),
                ('seller_phone', models.CharField(db_column='seller_ph', max_length=30, verbose_name='التليفون')),
                ('national_id', models.CharField(db_column='nid', max_length=20, verbose_name='رقم البطاقة')),
                ('serial_number', models.CharField(db_column='serial', max_length=50, verbose_name='السيريال / IMEI')),
                ('device_specs', models.TextField(db_column='specs', verbose_name='مواصفات الجهاز')),
                ('model_name', models.CharField(blank=True, db_column='model', max_length=120, verbose_name='الموديل')),
                ('storage', models.CharField(blank=True, db_column='stor', max_length=40, verbose_name='السعة')),
                ('color', models.CharField(blank=True, db_column='clr', max_length=40, verbose_name='اللون')),
                ('purchase_amount', models.DecimalField(db_column='amt', decimal_places=2, max_digits=14, verbose_name='مبلغ الشراء')),
                ('sale_price', models.DecimalField(db_column='sale', decimal_places=2, default=0, max_digits=14, verbose_name='سعر البيع المقترح')),
                ('payment_type', models.CharField(choices=[('cash', 'نقدي'), ('bank', 'بنك')], db_column='pay_typ', default='cash', max_length=10)),
                ('id_card_photo', models.ImageField(blank=True, db_column='id_img', null=True, upload_to='buyback/ids/', verbose_name='صورة البطاقة')),
                ('status', models.CharField(choices=[('draft', 'مسودة'), ('posted', 'مرحّل')], db_column='st', default='draft', max_length=10)),
                ('notes', models.TextField(blank=True, db_column='nt', verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='crt')),
                ('bank', models.ForeignKey(blank=True, db_column='bank_id', null=True, on_delete=django.db.models.deletion.PROTECT, to='treasury.bank', verbose_name='البنك')),
                ('branch', models.ForeignKey(blank=True, db_column='br_id', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='buybacks', to='pharmacy.branch')),
                ('created_by', models.ForeignKey(db_column='uid', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='buybacks', to=settings.AUTH_USER_MODEL)),
                ('product', models.ForeignKey(db_column='prod_id', on_delete=django.db.models.deletion.PROTECT, related_name='buybacks', to='inventory.product', verbose_name='الصنف')),
                ('warehouse', models.ForeignKey(db_column='wh_id', on_delete=django.db.models.deletion.PROTECT, related_name='buybacks', to='inventory.warehouse', verbose_name='المخزن')),
            ],
            options={
                'verbose_name': 'شراء من فرد',
                'verbose_name_plural': 'مشتريات من أفراد',
                'db_table': 'bb_doc',
                'ordering': ['-date', '-id'],
            },
        ),
    ]
