from django.db import migrations, models


def backfill_log_numbers(apps, schema_editor):
    ActivityLog = apps.get_model('pharmacy', 'ActivityLog')
    for n, log in enumerate(ActivityLog.objects.order_by('id', 'created_at'), start=1):
        log.log_no = str(n)
        log.save(update_fields=['log_no'])


class Migration(migrations.Migration):

    dependencies = [
        ('pharmacy', '0008_short_table_names'),
    ]

    operations = [
        migrations.AddField(
            model_name='activitylog',
            name='log_no',
            field=models.CharField(
                blank=True, db_column='no', max_length=20,
                null=True, unique=True, verbose_name='رقم الحركة',
            ),
        ),
        migrations.RunPython(backfill_log_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='activitylog',
            name='log_no',
            field=models.CharField(
                blank=True, db_column='no', max_length=20,
                unique=True, verbose_name='رقم الحركة',
            ),
        ),
    ]
