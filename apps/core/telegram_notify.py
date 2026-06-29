"""إرسال إشعارات تليجرام عند تسجيل حركة في سجل النظام."""
import json
import logging
import urllib.error
import urllib.request

from django.utils import timezone

logger = logging.getLogger(__name__)


def _get_settings():
    try:
        from apps.shop.models import TelegramSettings
        return TelegramSettings.get_solo()
    except Exception:
        return None


def send_telegram_message(text: str) -> bool:
    cfg = _get_settings()
    if not cfg or not cfg.enabled or not cfg.bot_token or not cfg.chat_id:
        return False
    url = f'https://api.telegram.org/bot{cfg.bot_token}/sendMessage'
    payload = json.dumps({
        'chat_id': cfg.chat_id,
        'text': text[:4000],
        'parse_mode': 'HTML',
        'disable_web_page_preview': True,
    }).encode('utf-8')
    req = urllib.request.Request(
        url, data=payload, headers={'Content-Type': 'application/json'}, method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning('Telegram notify failed: %s', exc)
        return False


def notify_activity(log, action_label=''):
    """إشعار تليجرام بكل تفاصيل سجل الحركة."""
    from apps.shop.models import ActivityLog

    if not action_label:
        action_label = dict(ActivityLog.Action.choices).get(log.action, log.action)

    when = timezone.localtime(log.created_at).strftime('%Y-%m-%d %H:%M')
    parts = [
        f'<b>LyomasPhone — حركة #{log.log_no}</b>',
        f'🕐 {when}',
        f'👤 {log.username}',
        f'📂 {log.section or "—"}',
        f'⚡ {action_label}',
    ]
    if log.object_ref:
        parts.append(f'🔖 مرجع المستند: <b>{log.object_ref}</b>')
    if log.description:
        parts.append(f'\n📝 {log.description}')
    if log.branch_id:
        branch = getattr(log, 'branch', None)
        if branch is None:
            try:
                from apps.shop.models import Branch
                branch = Branch.objects.filter(pk=log.branch_id).only('name').first()
            except Exception:
                branch = None
        if branch:
            parts.append(f'🏢 فرع: {branch.name}')
    if log.ip_address:
        parts.append(f'🌐 IP: {log.ip_address}')
    send_telegram_message('\n'.join(parts))
