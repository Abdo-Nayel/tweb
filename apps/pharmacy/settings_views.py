from functools import partial

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q

from apps.core.delete_checks import (
    branch_blockers, bank_blockers, user_blockers,
)
from apps.core.permissions import require_module, user_can
from apps.core.permission_groups import MODULE_GROUPS
from apps.core.dashboard_shortcuts import DASHBOARD_SHORTCUTS, DEFAULT_DASHBOARD_SHORTCUTS, SHORTCUTS_BY_KEY
from apps.core.views import delete_confirm
from apps.core.pagination import paginate_queryset
from apps.pharmacy.models import ShopProfile, Branch, BarcodeLabelSettings, ReceiptSettings, TelegramSettings
from apps.treasury.models import Bank
from apps.treasury.banks import banks_for_user
from apps.users.models import UserModuleAccess

User = get_user_model()
ALL_MODULES = UserModuleAccess.Module.choices


from apps.core.codes import next_serial


def _next_code(model, prefix, field='code'):
    return next_serial(model, field)


@login_required
@require_module('settings', 'view')
def settings_home(request):
    return render(request, 'settings/home.html', {'page_title': 'الإعدادات'})


@login_required
@require_module('settings', 'view')
def shop_profile_form(request):
    profile = ShopProfile.objects.first()
    if request.method == 'POST':
        data = {
            'name': request.POST['name'],
            'owner_name': request.POST.get('owner_name', ''),
            'phone': request.POST.get('phone', ''),
            'address': request.POST.get('address', ''),
            'tax_number': request.POST.get('tax_number', ''),
        }
        if profile:
            for k, v in data.items():
                setattr(profile, k, v)
            profile.save()
        else:
            ShopProfile.objects.create(**data)
        from django.core.cache import cache
        cache.delete('shop_profile')
        cache.delete('pharmacy_profile')
        messages.success(request, 'تم حفظ بيانات المحل')
        return redirect('settings_home')
    return render(request, 'settings/shop_form.html', {
        'page_title': 'بيانات المحل',
        'profile': profile,
    })


pharmacy_profile_form = shop_profile_form


# ─── الفروع ───
@login_required
@require_module('settings', 'view')
def branch_list(request):
    q = request.GET.get('q', '')
    items = Branch.objects.all()
    if q:
        items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'settings/branch_list.html', {
        'page_title': 'الفروع',
        'items': page_obj,
        'page_obj': page_obj,
        'q': q,
    })


@login_required
@require_module('settings', 'add')
def branch_form(request, pk=None):
    obj = get_object_or_404(Branch, pk=pk) if pk else None
    if request.method == 'POST':
        data = {
            'code': request.POST.get('code') or _next_code(Branch, 'BR'),
            'name': request.POST['name'],
            'address': request.POST.get('address', ''),
            'phone': request.POST.get('phone', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
            messages.success(request, 'تم تحديث الفرع')
        else:
            Branch.objects.create(**data)
            messages.success(request, 'تم إضافة الفرع')
        return redirect('branch_list')
    return render(request, 'settings/branch_form.html', {
        'page_title': 'تعديل فرع' if obj else 'إضافة فرع',
        'obj': obj,
        'suggested_code': obj.code if obj else _next_code(Branch, 'BR'),
    })


@login_required
def branch_delete(request, pk):
    return delete_confirm(
        request, Branch, pk, branch_blockers, 'branch_list', 'settings',
        object_label=lambda o: o.name, page_title='حذف فرع',
    )


# ─── البنوك ───
@login_required
@require_module('settings', 'view')
def bank_list(request):
    q = request.GET.get('q', '')
    items = banks_for_user(request.user, active_only=False)
    if q:
        items = items.filter(Q(name__icontains=q) | Q(code__icontains=q))
    items = items.order_by('name', 'code')
    return render(request, 'settings/bank_list.html', {
        'page_title': 'البنوك',
        'items': items,
        'q': q,
    })


@login_required
@require_module('settings', 'add')
def bank_form(request, pk=None):
    obj = get_object_or_404(Bank, pk=pk) if pk else None

    if request.method == 'POST':
        data = {
            'code': request.POST.get('code') or _next_code(Bank, 'BNK'),
            'name': request.POST['name'],
            'account_number': request.POST.get('account_number', ''),
            'branch_id': None,
            'notes': request.POST.get('notes', ''),
            'is_active': request.POST.get('is_active') == 'on',
        }
        if obj:
            for k, v in data.items():
                setattr(obj, k, v)
            obj.save()
            messages.success(request, 'تم تحديث الحساب البنكي')
        else:
            Bank.objects.create(**data)
            messages.success(request, 'تم إضافة الحساب البنكي')
        return redirect('bank_list')
    return render(request, 'settings/bank_form.html', {
        'page_title': 'تعديل حساب بنكي' if obj else 'إضافة حساب بنكي',
        'obj': obj,
        'suggested_code': obj.code if obj else _next_code(Bank, 'BNK'),
    })


@login_required
def bank_delete(request, pk):
    return delete_confirm(
        request, Bank, pk, bank_blockers, 'bank_list', 'settings',
        object_label=lambda o: o.name, page_title='حذف بنك',
    )


# ─── المستخدمون ───
@login_required
@require_module('settings', 'view')
def user_list(request):
    q = request.GET.get('q', '')
    items = User.objects.select_related('branch').all()
    if q:
        items = items.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    page_obj = paginate_queryset(request, items, per_page=25)
    return render(request, 'settings/user_list.html', {
        'page_title': 'المستخدمون',
        'items': page_obj,
        'page_obj': page_obj,
        'q': q,
    })


@login_required
@require_module('settings', 'add')
def user_form(request, pk=None):
    obj = get_object_or_404(User, pk=pk) if pk else None
    branches = Branch.objects.filter(is_active=True)
    existing_access = {a.module: a for a in obj.module_access.all()} if obj else {}

    def _access_row(mod, label):
        acc = existing_access.get(mod)
        return {
            'module': mod,
            'label': label,
            'can_view': acc.can_view if acc else (not obj),
            'can_add': acc.can_add if acc else False,
            'can_edit': acc.can_edit if acc else False,
            'can_delete': acc.can_delete if acc else False,
        }

    permission_groups = []
    for group in MODULE_GROUPS:
        permission_groups.append({
            **group,
            'rows': [_access_row(mod, label) for mod, label in group['modules']],
        })

    selected_shortcuts = set(obj.dashboard_shortcuts if obj and obj.dashboard_shortcuts else DEFAULT_DASHBOARD_SHORTCUTS)

    if request.method == 'POST':
        username = request.POST['username'].strip()
        if obj:
            obj.first_name = request.POST.get('first_name', '')
            obj.last_name = request.POST.get('last_name', '')
            obj.email = request.POST.get('email', '')
            obj.phone = request.POST.get('phone', '')
            obj.role = request.POST.get('role', User.Role.CASHIER)
            obj.branch_id = request.POST.get('branch') or None
            obj.is_active = request.POST.get('is_active') == 'on'
            if request.POST.get('password'):
                obj.set_password(request.POST['password'])
            obj.save()
            user = obj
            messages.success(request, 'تم تحديث المستخدم')
        else:
            if User.objects.filter(username=username).exists():
                messages.error(request, 'اسم المستخدم موجود مسبقاً')
                return redirect('user_add')
            user = User.objects.create_user(
                username=username,
                password=request.POST['password'],
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                email=request.POST.get('email', ''),
                phone=request.POST.get('phone', ''),
                role=request.POST.get('role', User.Role.CASHIER),
                branch_id=request.POST.get('branch') or None,
                is_active=request.POST.get('is_active') == 'on',
            )
            messages.success(request, 'تم إضافة المستخدم')

        for module, _label in ALL_MODULES:
            UserModuleAccess.objects.update_or_create(
                user=user,
                module=module,
                defaults={
                    'can_view': request.POST.get(f'view_{module}') == 'on',
                    'can_add': request.POST.get(f'add_{module}') == 'on',
                    'can_edit': request.POST.get(f'edit_{module}') == 'on',
                    'can_delete': request.POST.get(f'delete_{module}') == 'on',
                },
            )

        shortcuts = [
            key for key in SHORTCUTS_BY_KEY
            if request.POST.get(f'shortcut_{key}') == 'on'
        ]
        user.dashboard_shortcuts = shortcuts
        user.save(update_fields=['dashboard_shortcuts'])
        return redirect('user_list')

    return render(request, 'settings/user_form.html', {
        'page_title': 'تعديل مستخدم' if obj else 'إضافة مستخدم',
        'obj': obj,
        'branches': branches,
        'permission_groups': permission_groups,
        'dashboard_shortcut_options': DASHBOARD_SHORTCUTS,
        'selected_shortcuts': selected_shortcuts,
        'roles': User.Role.choices,
    })


@login_required
def user_delete(request, pk):
    def blockers(obj):
        reasons = user_blockers(obj)
        if obj.pk == request.user.pk:
            reasons.append('لا يمكن حذف المستخدم الحالي')
        return reasons

    return delete_confirm(
        request, User, pk, blockers, 'user_list', 'settings',
        object_label=lambda o: o.username, page_title='حذف مستخدم',
    )


# ─── ليبل الباركود ───
@login_required
@require_module('settings', 'view')
def barcode_settings(request):
    settings_obj = BarcodeLabelSettings.get_solo()
    if request.method == 'POST':
        settings_obj.label_width_mm = int(request.POST.get('label_width_mm', 50))
        settings_obj.label_height_mm = int(request.POST.get('label_height_mm', 30))
        settings_obj.show_product_name = request.POST.get('show_product_name') == 'on'
        settings_obj.show_sku = request.POST.get('show_sku') == 'on'
        settings_obj.show_price = request.POST.get('show_price') == 'on'
        settings_obj.show_company = request.POST.get('show_company') == 'on'
        settings_obj.font_size = int(request.POST.get('font_size', 10))
        settings_obj.barcode_height = int(request.POST.get('barcode_height', 40))
        settings_obj.copies_default = int(request.POST.get('copies_default', 1))
        settings_obj.code_type = request.POST.get('code_type', 'barcode')
        settings_obj.save()
        messages.success(request, 'تم حفظ إعدادات الليبل')
        return redirect('barcode_settings')
    return render(request, 'settings/barcode_settings.html', {
        'page_title': 'إعدادات ليبل الباركود',
        'settings': settings_obj,
    })


# ─── إيصال البيع ───
@login_required
@require_module('settings', 'view')
def receipt_settings(request):
    settings_obj = ReceiptSettings.get_solo()
    profile = ShopProfile.objects.first()
    if request.method == 'POST':
        settings_obj.header_text = request.POST.get('header_text', '')
        settings_obj.footer_text = request.POST.get('footer_text', '')
        settings_obj.use_shop_logo = request.POST.get('use_shop_logo') == 'on'
        settings_obj.show_logo = request.POST.get('show_logo') == 'on'
        settings_obj.paper_width_mm = int(request.POST.get('paper_width_mm', 80))
        settings_obj.title_font_size = int(request.POST.get('title_font_size', 15))
        settings_obj.body_font_size = int(request.POST.get('body_font_size', 12))
        settings_obj.show_cashier = request.POST.get('show_cashier') == 'on'
        settings_obj.show_customer = request.POST.get('show_customer') == 'on'
        settings_obj.show_discount = request.POST.get('show_discount') == 'on'
        settings_obj.auto_print = request.POST.get('auto_print') == 'on'
        if request.FILES.get('receipt_logo'):
            settings_obj.receipt_logo = request.FILES['receipt_logo']
        settings_obj.save()
        messages.success(request, 'تم حفظ إعدادات الإيصال')
        return redirect('receipt_settings')
    return render(request, 'settings/receipt_settings.html', {
        'page_title': 'إعدادات إيصال البيع',
        'settings': settings_obj,
        'profile': profile,
    })


# ─── تليجرام ───
@login_required
@require_module('settings', 'view')
def telegram_settings(request):
    settings_obj = TelegramSettings.get_solo()
    if request.method == 'POST':
        settings_obj.bot_token = request.POST.get('bot_token', '').strip()
        settings_obj.chat_id = request.POST.get('chat_id', '').strip()
        settings_obj.enabled = request.POST.get('enabled') == 'on'
        settings_obj.notify_on_login = request.POST.get('notify_on_login') == 'on'
        settings_obj.save()
        messages.success(request, 'تم حفظ إعدادات تليجرام')
        if request.POST.get('test') == '1':
            from apps.core.telegram_notify import send_telegram_message
            ok = send_telegram_message('✅ LyomasPhone — رسالة اختبار من النظام')
            if ok:
                messages.success(request, 'تم إرسال رسالة الاختبار')
            else:
                messages.error(request, 'فشل الإرسال — تحقق من Token و Chat ID')
        return redirect('telegram_settings')
    return render(request, 'settings/telegram_settings.html', {
        'page_title': 'إشعارات تليجرام',
        'settings': settings_obj,
    })
