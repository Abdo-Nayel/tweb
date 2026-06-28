#!/bin/bash
# تشخيص سريع — bash deploy/diagnose-tweb.sh
APP_DIR="/var/www/tweb"
DOMAIN="tweb.erpbylyomastech.com"

echo "=== DNS ==="
getent hosts "$DOMAIN" || echo "DNS: غير محلول"

echo ""
echo "=== PostgreSQL ==="
if [ -f "$APP_DIR/.env" ]; then
  set -a; source "$APP_DIR/.env"; set +a
  PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -U "${DB_USER:-tweb}" -d "${DB_NAME:-tweb}" -c 'SELECT 1;' 2>&1 || echo "DB: فشل الاتصال"
else
  echo ".env غير موجود"
fi

echo ""
echo "=== tweb service ==="
systemctl is-active tweb 2>&1 || true
systemctl is-enabled tweb 2>&1 || true

echo ""
echo "=== gunicorn.sock ==="
ls -la "$APP_DIR/gunicorn.sock" 2>&1 || echo "لا يوجد socket"

echo ""
echo "=== nginx ==="
sudo nginx -t 2>&1
ls -la /etc/nginx/sites-enabled/ 2>&1

echo ""
echo "=== curl local ==="
curl -sI -H "Host: $DOMAIN" http://127.0.0.1/ 2>&1 | head -8

echo ""
echo "=== آخر أخطاء gunicorn ==="
sudo tail -15 /var/log/tweb/error.log 2>&1 || sudo journalctl -u tweb -n 15 --no-pager
