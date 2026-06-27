from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.codes import generate_product_barcode
from apps.parties.models import Supplier, Customer
from apps.inventory.models import Warehouse, DrugCategory, DrugCompany, Product
from apps.pharmacy.models import Branch
from apps.treasury.models import Bank, ExpenseCategory
from apps.purchases.models import PurchaseInvoice
from apps.sales.models import SalesInvoice
from apps.users.models import User


MODELS = [
    Branch, Warehouse, DrugCategory, DrugCompany, Supplier, Customer,
    Bank, ExpenseCategory,
]


class Command(BaseCommand):
    help = 'ترقيم الأكواد 1,2,3... وتفعيل الموردين وتوليد الباركود'

    @transaction.atomic
    def handle(self, *args, **options):
        for model in MODELS:
            field = 'code'
            for i, obj in enumerate(model.objects.order_by('id'), start=1):
                setattr(obj, field, str(i))
                obj.save(update_fields=[field])
            self.stdout.write(f'{model.__name__}: renumbered')

        for i, p in enumerate(Product.objects.order_by('id'), start=1):
            p.sku = str(i)
            p.barcode = ''
            p.save()
            p.barcode = generate_product_barcode(p)
            p.save(update_fields=['barcode'])

        for i, inv in enumerate(PurchaseInvoice.objects.order_by('id'), start=1):
            inv.invoice_number = str(i)
            inv.save(update_fields=['invoice_number'])
        for i, inv in enumerate(SalesInvoice.objects.order_by('id'), start=1):
            inv.invoice_number = str(i)
            inv.save(update_fields=['invoice_number'])

        for i, u in enumerate(User.objects.order_by('id'), start=1):
            u.code = str(i)
            u.save(update_fields=['code'])

        n = Supplier.objects.update(is_active=True)
        c = Customer.objects.update(is_active=True)
        self.stdout.write(self.style.SUCCESS(f'Done. Suppliers activated: {n}, Customers activated: {c}'))
