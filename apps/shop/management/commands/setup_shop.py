from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from apps.shop.models import ShopProfile
from apps.users.models import UserModuleAccess


class Command(BaseCommand):
    help = 'إعداد النظام الأولي — مدير نظام فقط'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='admin')
        parser.add_argument('--password', default='admin123')
        parser.add_argument('--shop-name', default='')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        password = options['password']

        if not User.objects.filter(username=username).exists():
            user = User.objects.create_superuser(
                username=username, password=password, role=User.Role.ADMIN,
            )
            for module, _ in UserModuleAccess.Module.choices:
                UserModuleAccess.objects.create(
                    user=user, module=module,
                    can_view=True, can_add=True, can_edit=True, can_delete=True,
                )
            self.stdout.write(self.style.SUCCESS(f'User created: {username}'))
        else:
            self.stdout.write(f'User exists: {username}')

        if not ShopProfile.objects.exists():
            name = options['shop_name'] or 'محل التليفونات'
            ShopProfile.objects.create(name=name)
            self.stdout.write(self.style.SUCCESS(f'Shop profile: {name}'))

        self.stdout.write(self.style.SUCCESS('Setup complete — no sample inventory data added.'))
        self.stdout.write('Run: python manage.py runserver')
