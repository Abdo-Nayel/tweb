# Generated manually for LyomasPhone transformation

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0004_activitylog'),
    ]

    operations = [
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=3, unique=True, verbose_name='رمز ISO')),
                ('name', models.CharField(max_length=80, verbose_name='الاسم')),
                ('symbol', models.CharField(max_length=10, verbose_name='الرمز')),
                ('decimal_places', models.PositiveSmallIntegerField(default=2, verbose_name='الخانات العشرية')),
                ('is_active', models.BooleanField(default=True, verbose_name='نشط')),
            ],
            options={
                'verbose_name': 'عملة',
                'verbose_name_plural': 'العملات',
                'ordering': ['code'],
            },
        ),
        migrations.RenameModel(
            old_name='PharmacyProfile',
            new_name='ShopProfile',
        ),
        migrations.AlterModelTable(
            name='shopprofile',
            table='pharmacy_pharmacyprofile',
        ),
        migrations.AddField(
            model_name='shopprofile',
            name='country',
            field=models.CharField(blank=True, default='EG', max_length=80, verbose_name='الدولة'),
        ),
        migrations.AddField(
            model_name='shopprofile',
            name='default_language',
            field=models.CharField(default='ar', max_length=5, verbose_name='اللغة الافتراضية'),
        ),
        migrations.AddField(
            model_name='shopprofile',
            name='timezone',
            field=models.CharField(default='Africa/Cairo', max_length=50, verbose_name='المنطقة الزمنية'),
        ),
        migrations.AddField(
            model_name='shopprofile',
            name='default_currency',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='shops', to='pharmacy.currency', verbose_name='عملة النظام',
            ),
        ),
        migrations.AddField(
            model_name='branch',
            name='country',
            field=models.CharField(blank=True, max_length=80, verbose_name='الدولة'),
        ),
        migrations.AddField(
            model_name='branch',
            name='currency',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='branches', to='pharmacy.currency', verbose_name='عملة الفرع',
            ),
        ),
        migrations.AlterField(
            model_name='shopprofile',
            name='name',
            field=models.CharField(max_length=200, verbose_name='اسم المحل'),
        ),
        migrations.AlterField(
            model_name='receiptsettings',
            name='footer_text',
            field=models.TextField(blank=True, default='نتمنى لكم تجربة ممتعة', verbose_name='نص الفوتر'),
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(
                    model_name='receiptsettings',
                    old_name='use_pharmacy_logo',
                    new_name='use_shop_logo',
                ),
            ],
        ),
    ]
