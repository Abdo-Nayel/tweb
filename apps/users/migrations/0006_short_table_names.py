from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_phone_shop_transform'),
    ]

    operations = [
        migrations.AlterModelTable(name='user', table='usr'),
        migrations.AlterModelTable(name='usermoduleaccess', table='usr_mod'),
    ]
