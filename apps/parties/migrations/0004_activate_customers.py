from django.db import migrations


def activate_customers(apps, schema_editor):
    Customer = apps.get_model('parties', 'Customer')
    Customer.objects.filter(is_active=False).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [
        ('parties', '0003_sales_pos_customer_payment'),
    ]

    operations = [
        migrations.RunPython(activate_customers, migrations.RunPython.noop),
    ]
