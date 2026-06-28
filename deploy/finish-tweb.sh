#!/bin/bash
# إكمال تثبيت tweb بعد clone يدوي — شغّله من /var/www/tweb
set -euo pipefail

APP_DIR="/var/www/tweb"
DOMAIN="tweb.erpbylyomastech.com"
SERVER_IP="${SERVER_IP:-162.0.237.222}"

cd "$APP_DIR"

if [ ! -f .env ]; then
  echo "خطأ: ملف .env غير موجود في $APP_DIR"
  exit 1
fi

# قراءة DB_PASSWORD من .env
set -a
source .env
set +a

if [ -z "${DB_PASSWORD:-}" ]; then
  echo "خطأ: DB_PASSWORD غير موجود في .env"
  exit 1
fi

echo "==> 1) PostgreSQL"
chmod +x deploy/setup-postgres.sh
export DB_NAME="${DB_NAME:-tweb}"
export DB_USER="${DB_USER:-tweb}"
bash deploy/setup-postgres.sh

echo "==> 2) اختبار اتصال DB"
PGPASSWORD="$DB_PASSWORD" psql -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" -c 'SELECT 1;' >/dev/null
echo "    DB OK"

echo "==> 3) Python + Django"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r Requirements.txt

# تأكد ALLOWED_HOSTS فيها IP السيرفر
if ! grep -q "$SERVER_IP" .env; then
  sed -i "s|^DJANGO_ALLOWED_HOSTS=.*|DJANGO_ALLOWED_HOSTS=${DOMAIN},${SERVER_IP},localhost,127.0.0.1|" .env
fi
if ! grep -q "http://${DOMAIN}" .env; then
  sed -i "s|^DJANGO_CSRF_TRUSTED_ORIGINS=.*|DJANGO_CSRF_TRUSTED_ORIGINS=https://${DOMAIN},http://${DOMAIN}|" .env
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if ! python manage.py shell -c "from apps.users.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
  python manage.py setup_shop --username admin --password admin123 --shop-name "محل التليفونات"
fi

echo "==> 4) صلاحيات"
sudo mkdir -p /var/log/tweb "$APP_DIR/media" "$APP_DIR/staticfiles"
sudo chown -R softwarehouse:www-data "$APP_DIR/media" /var/log/tweb
chmod 750 "$APP_DIR"
chmod 640 .env

echo "==> 5) systemd (tweb)"
sudo cp deploy/tweb.service /etc/systemd/system/tweb.service
sudo systemctl daemon-reload
sudo systemctl enable tweb
sudo systemctl restart tweb
sleep 2

if [ ! -S "$APP_DIR/gunicorn.sock" ]; then
  echo "خطأ: gunicorn.sock غير موجود — راجع:"
  sudo journalctl -u tweb -n 30 --no-pager
  exit 1
fi
sudo chmod 660 "$APP_DIR/gunicorn.sock" 2>/dev/null || true
sudo chgrp www-data "$APP_DIR/gunicorn.sock" 2>/dev/null || true

echo "==> 6) nginx"
sudo cp deploy/nginx-tweb.conf /etc/nginx/sites-available/tweb
sudo ln -sf /etc/nginx/sites-available/tweb /etc/nginx/sites-enabled/tweb
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "تم الإعداد"
echo ""
echo "اختبار محلي:"
curl -sI -H "Host: ${DOMAIN}" http://127.0.0.1/ | head -5 || true
echo ""
echo "من المتصفح:"
echo "  http://${DOMAIN}"
echo "  http://${SERVER_IP}  (لو DNS لسه مش شغال)"
echo ""
echo "الدخول: admin / admin123"
echo ""
echo "لو مش شغال:"
echo "  sudo systemctl status tweb"
echo "  sudo tail -30 /var/log/tweb/error.log"
echo "  sudo journalctl -u tweb -n 30 --no-pager"
echo "=========================================="
