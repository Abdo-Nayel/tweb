# Fix DB columns skipped by 0004 SeparateDatabaseAndState (state-only renames).

from django.db import migrations


def _table_columns(schema_editor, table):
    with schema_editor.connection.cursor() as cursor:
        desc = schema_editor.connection.introspection.get_table_description(cursor, table)
    return {col.name for col in desc}


def rename_product_columns_forward(apps, schema_editor):
    table = 'inventory_product'
    cols = _table_columns(schema_editor, table)
    if 'company_id' in cols and 'brand_id' not in cols:
        schema_editor.execute(
            f'ALTER TABLE {table} RENAME COLUMN company_id TO brand_id'
        )
    if 'expiry_alert_days' in cols and 'warranty_months' not in cols:
        schema_editor.execute(
            f'ALTER TABLE {table} RENAME COLUMN expiry_alert_days TO warranty_months'
        )


def rename_product_columns_backward(apps, schema_editor):
    table = 'inventory_product'
    cols = _table_columns(schema_editor, table)
    if 'brand_id' in cols and 'company_id' not in cols:
        schema_editor.execute(
            f'ALTER TABLE {table} RENAME COLUMN brand_id TO company_id'
        )
    if 'warranty_months' in cols and 'expiry_alert_days' not in cols:
        schema_editor.execute(
            f'ALTER TABLE {table} RENAME COLUMN warranty_months TO expiry_alert_days'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_phone_shop_transform'),
    ]

    operations = [
        migrations.RunPython(rename_product_columns_forward, rename_product_columns_backward),
    ]
