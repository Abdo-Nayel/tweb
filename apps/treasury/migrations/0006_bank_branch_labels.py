from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('treasury', '0005_entity_codes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bank',
            options={
                'ordering': ['branch__code', 'code'],
                'verbose_name': 'بنك',
                'verbose_name_plural': 'البنوك',
            },
        ),
        migrations.AlterField(
            model_name='bank',
            name='name',
            field=models.CharField(max_length=120, verbose_name='اسم الحساب البنكي'),
        ),
    ]
