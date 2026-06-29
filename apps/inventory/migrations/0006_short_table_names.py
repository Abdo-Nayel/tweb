from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0005_rename_product_company_to_brand'),
    ]

    operations = [
        migrations.AlterModelTable(name='warehouse', table='inv_wh'),
        migrations.AlterModelTable(name='productcategory', table='inv_cat'),
        migrations.AlterModelTable(name='brand', table='inv_brd'),
        migrations.AlterModelTable(name='product', table='inv_prd'),
        migrations.AlterModelTable(name='stocklot', table='inv_lot'),
        migrations.AlterModelTable(name='stockmovement', table='inv_mv'),
    ]
