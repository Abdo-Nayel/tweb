# Generated manually for LyomasPhone features

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('treasury', '0006_bank_branch_labels'),
    ]

    operations = [
        migrations.CreateModel(
            name='TreasuryMovement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('kind', models.CharField(choices=[('cash_in', 'إيداع نقدي'), ('cash_out', 'سحب نقدي'), ('bank_in', 'إيداع بنك'), ('bank_out', 'سحب بنك'), ('c2b', 'تحويل نقد → بنك'), ('b2c', 'تحويل بنك → نقد')], db_column='k', max_length=10, verbose_name='النوع')),
                ('amount', models.DecimalField(db_column='amt', decimal_places=2, max_digits=14, verbose_name='المبلغ')),
                ('date', models.DateField(db_column='dt', verbose_name='التاريخ')),
                ('notes', models.CharField(blank=True, db_column='nt', max_length=255, verbose_name='ملاحظات')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_column='crt')),
                ('bank', models.ForeignKey(blank=True, db_column='bank_id', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movements', to='treasury.bank', verbose_name='البنك')),
                ('created_by', models.ForeignKey(db_column='uid', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='treasury_movements', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'حركة خزينة',
                'verbose_name_plural': 'حركات الخزينة',
                'db_table': 'tr_mv',
                'ordering': ['-date', '-id'],
            },
        ),
    ]
