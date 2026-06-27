from apps.pharmacy.models import ActivityLog


def log_activity(request, action, section='', description='', object_ref=''):
    user = getattr(request, 'user', None)
    if user and not user.is_authenticated:
        user = None
    ip = request.META.get('REMOTE_ADDR') if request else None
    ActivityLog.objects.create(
        user=user,
        username=user.username if user else '—',
        action=action,
        section=section[:80] if section else '',
        description=description[:500] if description else '',
        object_ref=object_ref[:120] if object_ref else '',
        ip_address=ip,
        branch_id=getattr(user, 'branch_id', None) if user else None,
    )


def log_from_request(request):
    if request.method != 'POST' or not request.user.is_authenticated:
        return
    path = request.path.rstrip('/')
    action = ActivityLog.Action.UPDATE
    if 'delete' in path:
        action = ActivityLog.Action.DELETE
    elif '/add' in path or path.endswith('/add'):
        action = ActivityLog.Action.CREATE
    elif 'post' in request.POST or 'save_post' in request.POST:
        action = ActivityLog.Action.POST

    section = _section_from_path(path)
    desc = f'{request.method} {path}'
    if request.POST.get('username'):
        desc = f'عملية على {section}'
    log_activity(request, action, section=section, description=desc)


def _section_from_path(path):
    mapping = {
        '/sales': 'المبيعات',
        '/purchases': 'المشتريات',
        '/returns': 'المرتجعات',
        '/parties': 'الأطراف',
        '/inventory': 'المخزون',
        '/treasury': 'الخزينة',
        '/settings': 'الإعدادات',
    }
    for prefix, label in mapping.items():
        if path.startswith(prefix):
            return label
    return 'النظام'
