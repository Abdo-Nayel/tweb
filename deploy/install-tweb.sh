#!/bin/bash
# تثبيت LyomasPhone على tweb.erpbylyomastech.com
# على السيرفر (Ubuntu) كمستخدم softwarehouse:
#   DB_PASSWORD='كلمة-قوية' bash deploy/install-tweb.sh
set -euo pipefail

APP_DIR="/var/www/tweb"
REPO="https://github.com/Abdo-Nayel/tweb.git"
DOMAIN="tweb.erpbylyomastech.com"
SERVER_IP="${SERVER_IP:-162.0.237.222}"
DB_NAME="${DB_NAME:-tweb}"
DB_USER="${DB_USER:-tweb}"
DB_PASSWORD="${DB_PASSWORD:-}"
SHOP_NAME="${SHOP_NAME:-محل التليفونات}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin123}"

if [ -z "$DB_PASSWORD" ]; then
  echo "مطلوب: DB_PASSWORD='كلمة-قوية' bash deploy/install-tweb.sh"
  exit 1
fi

echo "==> إيقاف الخدمة (إن وُجدت)"
sudo systemctl stop tweb 2>/dev/null || true

echo "==> PostgreSQL + خطوط عربية"
sudo apt-get update -qq
sudo apt-get install -y postgresql postgresql-contrib fonts-noto-arabic nginx git python3-venv
sudo systemctl enable postgresql nginx
sudo systemctl start postgresql

echo "==> مجلدات التطبيق"
sudo mkdir -p /var/log/tweb
if [ ! -d "$APP_DIR/.git" ]; then
  sudo rm -rf "$APP_DIR"
  sudo mkdir -p "$APP_DIR"
  sudo chown -R softwarehouse:www-data "$APP_DIR" /var/log/tweb
  echo "==> استنساخ المشروع"
  git clone "$REPO" "$APP_DIR"
else
  sudo chown -R softwarehouse:www-data "$APP_DIR" /var/log/tweb
  echo "==> المشروع موجود — git pull"
  cd "$APP_DIR"
  git pull origin main
fi

cd "$APP_DIR"
chmod +x deploy/setup-postgres.sh

export DB_NAME DB_USER DB_PASSWORD
bash deploy/setup-postgres.sh

echo "==> Python venv"
if [ ! -d venv ]; then
  python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r Requirements.txt

echo "==> .env"
if [ ! -f .env ]; then
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  cat > .env <<ENV
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=${SECRET}
DJANGO_ALLOWED_HOSTS=${DOMAIN},${SERVER_IP},localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://${DOMAIN},http://${DOMAIN}
DJANGO_SESSION_COOKIE_SECURE=False
DJANGO_CSRF_COOKIE_SECURE=False

DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
DB_HOST=127.0.0.1
DB_PORT=5432
ENV
  chmod 640 .env
else
  echo "    .env موجود — لم يُستبدَل"
fi

echo "==> migrate + static"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if ! python manage.py shell -c "from apps.users.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
  echo "==> إعداد المدير والمحل"
  python manage.py setup_shop --username "$ADMIN_USER" --password "$ADMIN_PASS" --shop-name "$SHOP_NAME"
fi

sudo mkdir -p "$APP_DIR/media"
sudo chown -R softwarehouse:www-data "$APP_DIR/media"

echo "==> systemd + nginx"
sudo cp deploy/tweb.service /etc/systemd/system/tweb.service
sudo systemctl daemon-reload
sudo systemctl enable tweb
sudo systemctl restart tweb

sudo cp deploy/nginx-tweb.conf /etc/nginx/sites-available/tweb
sudo ln -sf /etc/nginx/sites-available/tweb /etc/nginx/sites-enabled/tweb
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "=========================================="
echo "تم التثبيت — LyomasPhone / TWeb"
echo "الموقع: http://${DOMAIN}"
echo "الدخول: ${ADMIN_USER} / ${ADMIN_PASS}  (غيّر كلمة المرور فوراً)"
echo "حالة الخدمة: sudo systemctl status tweb"
echo ""
echo "DNS: تأكد أن A record لـ ${DOMAIN} → ${SERVER_IP}"
echo ""
echo "HTTPS (بعد ضبط DNS):"
echo "  cd $APP_DIR && CERTBOT_EMAIL='your@email.com' bash deploy/enable-ssl-tweb.sh"
echo "=========================================="
