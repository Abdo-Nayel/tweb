# Generated manually for LyomasPhone features

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0006_remove_multinational'),
    ]

    operations = [
        migrations.AddField(
            model_name='barcodelabelsettings',
            name='code_type',
            field=models.CharField(
                choices=[('barcode', 'باركود (CODE128)'), ('qr', 'QR Code')],
                default='barcode',
                max_length=10,
                verbose_name='نوع الكود',
            ),
        ),
        migrations.CreateModel(
            name='TelegramSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bot_token', models.CharField(blank=True, max_length=120, verbose_name='Bot Token')),
                ('chat_id', models.CharField(blank=True, max_length=40, verbose_name='Chat ID')),
                ('enabled', models.BooleanField(default=False, verbose_name='تفعيل الإشعارات')),
                ('notify_on_login', models.BooleanField(default=True, verbose_name='إشعار تسجيل الدخول')),
            ],
            options={
                'verbose_name': 'إعدادات تليجرام',
                'verbose_name_plural': 'إعدادات تليجرام',
                'db_table': 'tg_cfg',
            },
        ),
    ]
