# Generated manually for LyomasPhone features

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventory', '0004_phone_shop_transform'),
        ('treasury', '0007_treasury_movement'),
    ]

    operations = [
        migrations.CreateModel(
            name='RepairOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_no', models.CharField(db_column='no', max_length=20, unique=True, verbose_name='رقم الأمر')),
                ('date', models.DateField(db_column='dt', verbose_name='التاريخ')),
                ('customer_name', models.CharField(db_column='cust_nm', max_length=120, verbose_name='اسم العميل')),
                ('customer_phone', models.CharField(db_column='cust_ph', max_length=30, verbose_name='التليفون')),
                ('device_desc', models.CharField(db_column='dev', max_length=200, verbose_name='الجهاز')),
                ('problem', models.TextField(blank=True, db_column='prob', verbose_name='العطل')),
                ('labor_fee', models.DecimalField(db_column='labor', decimal_places=2, default=0, max_digits=12, verbose_name='أجر الصيانة')),
                ('parts_cost', models.DecimalField(db_column='parts', decimal_places=2, default=0, max_digits=12, verbose_name='تكلفة قطع الغيار')),
                ('total', models.DecimalField(db_column='tot', decimal_places=2, default=0, max_digits=14, verbose_name='الإجمالي')),
                ('deposit', models.DecimalField(db_column='dep', decimal_places=2, default=0, max_digits=14, verbose_name='العربون')),
                ('paid', models.DecimalField(db_column='paid', decimal_places=2, default=0, max_digits=14, verbose_name='المدفوع')),
                ('status', models.CharField(choices=[('open', 'مستلم'), ('working', 'جاري العمل'), ('ready', 'جاهز للاستلام'), ('done', 'مكتمل'), ('cancel', 'ملغي')], db_column='st', default='open', max_length=10, verbose_name='الحالة')),
                ('notes', models.TextField(blank=True, db_column='nt', verbose_name='ملاحظات')),
                ('stock_deducted', models.BooleanField(db_column='stk_ok', default=False, verbose_name='تم خصم المخزون')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='crt')),
                ('completed_at', models.DateTimeField(blank=True, db_column='done_at', null=True)),
                ('created_by', models.ForeignKey(db_column='uid', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='repair_orders', to=settings.AUTH_USER_MODEL)),
                ('warehouse', models.ForeignKey(db_column='wh_id', on_delete=django.db.models.deletion.PROTECT, related_name='repair_orders', to='inventory.warehouse', verbose_name='المخزن')),
            ],
            options={
                'verbose_name': 'أمر صيانة',
                'verbose_name_plural': 'أوامر الصيانة',
                'db_table': 'rep_ord',
                'ordering': ['-date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='RepairPart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.CharField(choices=[('stock', 'من المخزون'), ('external', 'مورد خارجي')], db_column='src', max_length=10, verbose_name='المصدر')),
                ('ext_desc', models.CharField(blank=True, db_column='ext_desc', max_length=255, verbose_name='بيان خارجي')),
                ('quantity', models.DecimalField(db_column='qty', decimal_places=2, default=1, max_digits=10, verbose_name='الكمية')),
                ('unit_cost', models.DecimalField(db_column='cost', decimal_places=2, default=0, max_digits=12, verbose_name='التكلفة')),
                ('order', models.ForeignKey(db_column='ord_id', on_delete=django.db.models.deletion.CASCADE, related_name='part_lines', to='repairs.repairorder')),
                ('product', models.ForeignKey(blank=True, db_column='prod_id', null=True, on_delete=django.db.models.deletion.PROTECT, to='inventory.product', verbose_name='المنتج')),
            ],
            options={
                'verbose_name': 'قطعة صيانة',
                'verbose_name_plural': 'قطع الصيانة',
                'db_table': 'rep_prt',
            },
        ),
        migrations.CreateModel(
            name='RepairPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_type', models.CharField(choices=[('cash', 'نقدي'), ('bank', 'بنك')], db_column='typ', default='cash', max_length=10)),
                ('amount', models.DecimalField(db_column='amt', decimal_places=2, max_digits=14)),
                ('is_deposit', models.BooleanField(db_column='is_dep', default=False, verbose_name='عربون')),
                ('notes', models.CharField(blank=True, db_column='nt', max_length=120)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='crt')),
                ('bank', models.ForeignKey(blank=True, db_column='bank_id', null=True, on_delete=django.db.models.deletion.PROTECT, to='treasury.bank')),
                ('created_by', models.ForeignKey(db_column='uid', null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('order', models.ForeignKey(db_column='ord_id', on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='repairs.repairorder')),
            ],
            options={
                'verbose_name': 'دفعة صيانة',
                'verbose_name_plural': 'دفعات الصيانة',
                'db_table': 'rep_pay',
                'ordering': ['created_at'],
            },
        ),
    ]
