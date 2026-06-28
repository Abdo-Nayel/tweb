"""إرسال إشعارات تليجرام عند تسجيل حركة في سجل النظام."""
import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


def _get_settings():
    try:
        from apps.pharmacy.models import TelegramSettings
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


def notify_activity(username, action_label, section, description, object_ref=''):
    parts = [f'<b>LyomasPhone</b>', f'👤 {username}', f'📂 {section or "—"}', f'⚡ {action_label}']
    if object_ref:
        parts.append(f'🔖 {object_ref}')
    if description:
        parts.append(f'\n{description}')
    send_telegram_message('\n'.join(parts))
