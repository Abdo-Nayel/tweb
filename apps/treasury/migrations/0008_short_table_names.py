from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('treasury', '0007_treasury_movement'),
    ]

    operations = [
        migrations.AlterModelTable(name='bank', table='try_bnk'),
        migrations.AlterModelTable(name='expensecategory', table='try_exp_cat'),
        migrations.AlterModelTable(name='expense', table='try_exp'),
        migrations.AlterModelTable(name='cashbox', table='try_cash'),
    ]
