from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parties', '0004_activate_customers'),
    ]

    operations = [
        migrations.AlterModelTable(name='supplier', table='pty_sup'),
        migrations.AlterModelTable(name='supplierpayment', table='pty_sup_pay'),
        migrations.AlterModelTable(name='customer', table='pty_cust'),
        migrations.AlterModelTable(name='customerpayment', table='pty_cust_pay'),
    ]
