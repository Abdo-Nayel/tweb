#!/bin/bash
# إصلاح يدوي كامل — شغّله من /var/www/tweb بعد رفع الملفات
#   cd /var/www/tweb && bash deploy/manual-fix.sh
set -euo pipefail

APP_DIR="/var/www/tweb"
DOMAIN="tweb.erpbylyomastech.com"
SERVER_IP="${SERVER_IP:-162.0.237.222}"
DB_NAME="${DB_NAME:-tweb}"
DB_USER="${DB_USER:-tweb}"
DB_PASSWORD="${DB_PASSWORD:-Lyo22999}"

cd "$APP_DIR"

echo "==> 1) PostgreSQL"
chmod +x deploy/setup-postgres.sh 2>/dev/null || true
export DB_NAME DB_USER DB_PASSWORD
bash deploy/setup-postgres.sh

echo "==> 2) .env (إعدادات مرنة للتجربة)"
SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))" 2>/dev/null || echo "change-me-manually")
cat > .env <<ENV
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=${SECRET}
DJANGO_ALLOWED_HOSTS=${DOMAIN},${SERVER_IP},localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://${DOMAIN},http://${DOMAIN},http://${SERVER_IP}
DJANGO_SESSION_COOKIE_SECURE=False
DJANGO_CSRF_COOKIE_SECURE=False

DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=127.0.0.1
DB_PORT=5432
ENV
chmod 640 .env

echo "==> 3) Python"
sudo apt-get install -y python3-venv python3-pip postgresql-client nginx 2>/dev/null || true
if [ ! -d venv ]; then python3 -m venv venv; fi
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r Requirements.txt

echo "==> 4) Django"
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
python manage.py setup_shop --username admin --password admin123 --shop-name "محل التليفونات" 2>/dev/null || true

echo "==> 5) صلاحيات"
sudo mkdir -p /var/log/tweb media staticfiles
sudo chown -R softwarehouse:www-data media /var/log/tweb
sudo chmod 775 media staticfiles 2>/dev/null || true

echo "==> 6) Gunicorn (systemd)"
sudo cp deploy/tweb.service /etc/systemd/system/tweb.service
sudo systemctl daemon-reload
sudo systemctl enable tweb
sudo systemctl restart tweb
sleep 2

if [ -S gunicorn.sock ]; then
  sudo chmod 660 gunicorn.sock
  sudo chgrp www-data gunicorn.sock
else
  echo "تحذير: gunicorn.sock غير موجود"
  sudo journalctl -u tweb -n 20 --no-pager
fi

echo "==> 7) Nginx"
sudo cp deploy/nginx-tweb.conf /etc/nginx/sites-available/tweb
sudo ln -sf /etc/nginx/sites-available/tweb /etc/nginx/sites-enabled/tweb
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "اختبار:"
curl -sI -H "Host: ${DOMAIN}" http://127.0.0.1/ | head -3
curl -sI http://127.0.0.1/ | head -3
echo ""
echo "افتح من المتصفح:"
echo "  http://${SERVER_IP}"
echo "  http://${DOMAIN}"
echo "  admin / admin123"
echo ""
echo "بعد ما يشتغل — ضيّق .env للدومين فقط + certbot"
echo "  sudo certbot --nginx -d ${DOMAIN}"
echo "=========================================="
