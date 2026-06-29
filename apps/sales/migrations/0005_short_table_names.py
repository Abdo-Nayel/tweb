from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0004_sales_line_unit_cost'),
    ]

    operations = [
        migrations.AlterModelTable(name='salesinvoice', table='sl_inv'),
        migrations.AlterModelTable(name='salesline', table='sl_ln'),
        migrations.AlterModelTable(name='salespayment', table='sl_pay'),
    ]
