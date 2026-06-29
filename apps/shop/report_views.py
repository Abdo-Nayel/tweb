from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from apps.core.activity import log_activity
from apps.core.ledger_export import export_table_pdf
from apps.core.permissions import require_module
from apps.shop.models import ActivityLog
from apps.shop.report_services import build_daily_report

User = get_user_model()


def _parse_date(value):
    if not value:
        return None
    try:
        d = datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None
    if d.year < 2000 or d.year > 2100:
        return None
    return d


@login_required
@require_module('daily_report')
def daily_report(request):
    today = timezone.localdate()
    date_from = _parse_date(request.GET.get('from')) or today
    date_to = _parse_date(request.GET.get('to')) or date_from
    if date_to < date_from:
        date_from, date_to = date_to, date_from

    data = build_daily_report(request.user, date_from, date_to)

    period_label = (
        str(date_from) if date_from == date_to
        else f'{date_from} — {date_to}'
    )

    if request.GET.get('export') == 'pdf':
        log_activity(
            request, ActivityLog.Action.EXPORT,
            section='تقرير يومي',
            description=f'تصدير PDF {period_label}',
        )
        title = f'تقرير الحركات — {period_label}'
        rows = [
            [str(m['date']), m['ref'] or '', m['desc'] or '',
             str(m['in']) if m['in'] else '', str(m['out']) if m['out'] else '']
            for m in data['movements']
        ]
        footer = [
            ['', '', 'إجمالي الوارد', str(data['total_in']), ''],
            ['', '', 'إجمالي الصادر', '', str(data['total_out'])],
            ['', '', 'صافي النقدية', str(data['net']), ''],
        ]
        return export_table_pdf(
            title=title,
            headers=['التاريخ', 'المرجع', 'البيان', 'وارد', 'صادر'],
            rows=rows,
            footer_rows=footer,
            filename=f'daily-report-{date_from}-to-{date_to}.pdf',
        )

    return render(request, 'reports/daily_report.html', {
        'data': data,
        'date_from': date_from,
        'date_to': date_to,
        'period_label': period_label,
    })


@login_required
@require_module('activity_log')
def activity_log(request):
    today = timezone.localdate()
    qs = ActivityLog.objects.select_related('user', 'branch').all()

    date_from = request.GET.get('from')
    date_to = request.GET.get('to')
    user_id = request.GET.get('user')
    action = request.GET.get('action')

    parsed_from = _parse_date(date_from)
    parsed_to = _parse_date(date_to)

    if parsed_from:
        qs = qs.filter(created_at__date__gte=parsed_from)
    if parsed_to:
        qs = qs.filter(created_at__date__lte=parsed_to)

    if user_id:
        qs = qs.filter(user_id=user_id)
    if action:
        qs = qs.filter(action=action)

    if request.user.branch_id and request.user.role != User.Role.ADMIN and not request.user.is_superuser:
        qs = qs.filter(branch_id=request.user.branch_id)

    logs = qs[:500]
    users = User.objects.filter(is_active=True).order_by('username')

    period_label = 'الكل'
    if parsed_from and parsed_to:
        period_label = str(parsed_from) if parsed_from == parsed_to else f'{parsed_from} — {parsed_to}'
    elif parsed_from:
        period_label = f'من {parsed_from}'
    elif parsed_to:
        period_label = f'حتى {parsed_to}'

    if request.GET.get('export') == 'pdf':
        log_activity(
            request, ActivityLog.Action.EXPORT,
            section='سجل الحركات',
            description=f'تصدير PDF {period_label}',
        )
        title = f'سجل الحركات — {period_label}'
        rows = [
            [
                log.log_no or '—',
                timezone.localtime(log.created_at).strftime('%Y-%m-%d %H:%M'),
                log.username,
                log.get_action_display(),
                log.section or '—',
                log.object_ref or '—',
                log.description or '—',
            ]
            for log in logs
        ]
        return export_table_pdf(
            title=title,
            headers=['رقم الحركة', 'الوقت', 'المستخدم', 'العملية', 'القسم', 'المرجع', 'التفاصيل'],
            rows=rows,
            filename='activity-log.pdf',
        )

    return render(request, 'reports/activity_log.html', {
        'logs': logs,
        'users': users,
        'actions': ActivityLog.Action.choices,
        'filters': {
            'from': date_from or '',
            'to': date_to or '',
            'user': user_id or '',
            'action': action or '',
        },
        'period_label': period_label,
    })
