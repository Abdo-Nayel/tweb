from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0005_phone_shop_transform'),
    ]

    operations = [
        migrations.RemoveField(model_name='branch', name='currency'),
        migrations.RemoveField(model_name='branch', name='country'),
        migrations.RemoveField(model_name='shopprofile', name='default_currency'),
        migrations.RemoveField(model_name='shopprofile', name='default_language'),
        migrations.RemoveField(model_name='shopprofile', name='timezone'),
        migrations.RemoveField(model_name='shopprofile', name='country'),
        migrations.RemoveField(model_name='shopprofile', name='currency'),
        migrations.DeleteModel(name='Currency'),
    ]
