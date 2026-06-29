from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('returns', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelTable(name='returndocument', table='rt_doc'),
        migrations.AlterModelTable(name='returnline', table='rt_ln'),
        migrations.AlterModelTable(name='returnpayment', table='rt_pay'),
    ]
