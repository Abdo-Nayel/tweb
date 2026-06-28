# Generated manually for LyomasPhone transformation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0003_warehouse_branch'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='DrugCategory',
            new_name='ProductCategory',
        ),
        migrations.AlterModelTable(
            name='productcategory',
            table='inventory_drugcategory',
        ),
        migrations.RenameModel(
            old_name='DrugCompany',
            new_name='Brand',
        ),
        migrations.AlterModelTable(
            name='brand',
            table='inventory_drugcompany',
        ),
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RenameField(model_name='product', old_name='company', new_name='brand'),
                migrations.RenameField(
                    model_name='product', old_name='expiry_alert_days', new_name='warranty_months',
                ),
                migrations.RenameField(
                    model_name='stocklot', old_name='batch_number', new_name='serial_number',
                ),
                migrations.RenameField(
                    model_name='stocklot', old_name='expiry_date', new_name='warranty_end',
                ),
            ],
        ),
        migrations.AddField(
            model_name='product',
            name='model_name',
            field=models.CharField(blank=True, max_length=120, verbose_name='الموديل'),
        ),
        migrations.AddField(
            model_name='product',
            name='storage',
            field=models.CharField(blank=True, max_length=40, verbose_name='السعة / الذاكرة'),
        ),
        migrations.AddField(
            model_name='product',
            name='color',
            field=models.CharField(blank=True, max_length=40, verbose_name='اللون'),
        ),
        migrations.AddField(
            model_name='product',
            name='condition',
            field=models.CharField(
                choices=[('new', 'جديد'), ('used', 'مستعمل'), ('refurb', 'مجدّد'), ('open_box', 'مفتوح العبوة')],
                default='new', max_length=10, verbose_name='الحالة',
            ),
        ),
        migrations.AddField(
            model_name='product',
            name='is_serialized',
            field=models.BooleanField(default=True, verbose_name='تتبع بالسيريال/IMEI'),
        ),
        migrations.AddField(
            model_name='stocklot',
            name='warranty_start',
            field=models.DateField(blank=True, null=True, verbose_name='بداية الضمان'),
        ),
        migrations.AlterField(
            model_name='product',
            name='name',
            field=models.CharField(max_length=200, verbose_name='اسم المنتج'),
        ),
        migrations.AlterField(
            model_name='product',
            name='unit',
            field=models.CharField(
                choices=[('piece', 'قطعة'), ('set', 'طقم'), ('box', 'علبة')],
                default='piece', max_length=10, verbose_name='الوحدة',
            ),
        ),
        migrations.AlterField(
            model_name='brand',
            name='country',
            field=models.CharField(blank=True, max_length=80, verbose_name='بلد المنشأ'),
        ),
    ]
