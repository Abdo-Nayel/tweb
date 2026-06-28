# Generated manually for LyomasPhone transformation

from django.db import migrations, models


def migrate_pharmacist_role(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(role='pharmacist').update(role='store_manager')


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_user_dashboard_shortcuts'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'مدير'),
                    ('store_manager', 'مدير فرع'),
                    ('cashier', 'كاشير'),
                    ('accountant', 'محاسب'),
                ],
                default='cashier',
                max_length=20,
            ),
        ),
        migrations.RunPython(migrate_pharmacist_role, migrations.RunPython.noop),
    ]
