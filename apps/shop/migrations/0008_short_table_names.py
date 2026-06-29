from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0007_features_pos_repairs_tg'),
    ]

    operations = [
        migrations.AlterModelTable(name='shopprofile', table='shop_prf'),
        migrations.AlterModelTable(name='branch', table='shop_br'),
        migrations.AlterModelTable(name='barcodelabelsettings', table='lbl_cfg'),
        migrations.AlterModelTable(name='receiptsettings', table='rcp_cfg'),
        migrations.AlterModelTable(name='activitylog', table='act_log'),
    ]
