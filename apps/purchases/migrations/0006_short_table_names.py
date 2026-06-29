from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('purchases', '0005_purchaseinvoice_branch'),
    ]

    operations = [
        migrations.AlterModelTable(name='purchaseinvoice', table='pu_inv'),
        migrations.AlterModelTable(name='purchaseline', table='pu_ln'),
        migrations.AlterModelTable(name='purchasepayment', table='pu_pay'),
    ]
