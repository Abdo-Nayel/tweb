#!/bin/bash
# تشغيل على السيرفر Ubuntu كـ softwarehouse (مع sudo لـ nginx/systemd)
set -euo pipefail

APP_DIR="/var/www/parma"
REPO="https://github.com/Abdo-Nayel/Parma.git"
DOMAIN="pweb.erpbylyomastech.com"

echo "==> إنشاء مجلد التطبيق"
sudo mkdir -p "$APP_DIR" /var/log/parma
sudo chown -R softwarehouse:www-data "$APP_DIR" /var/log/parma

if [ ! -d "$APP_DIR/.git" ]; then
  echo "==> استنساخ المشروع"
  git clone "$REPO" "$APP_DIR"
else
  echo "==> تحديث المشروع"
  cd "$APP_DIR"
  git pull origin main
fi

cd "$APP_DIR"

echo "==> Python venv"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r Requirements.txt

echo "==> Arabic fonts (PDF export fallback if static/fonts missing)"
sudo apt-get install -y fonts-noto-arabic || true

if [ ! -f .env ]; then
  echo "==> إنشاء .env من المثال — عدّل SECRET_KEY!"
  cp deploy/.env.example .env
  SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  sed -i "s/غيّر-هذا-لمفتاح-عشوائي-طويل-جداً/$SECRET/" .env
fi

echo "==> migrate + static"
python manage.py migrate --noinput
python manage.py collectstatic --noinput

if ! python manage.py shell -c "from apps.users.models import User; exit(0 if User.objects.filter(is_superuser=True).exists() else 1)" 2>/dev/null; then
  echo "==> إنشاء مستخدم مدير (غيّر كلمة المرور بعد أول دخول)"
  python manage.py setup_pharmacy
fi

echo "==> systemd"
sudo cp deploy/gunicorn.service /etc/systemd/system/parma.service
sudo systemctl daemon-reload
sudo systemctl enable parma
sudo systemctl restart parma

echo "==> nginx"
sudo cp deploy/nginx-parma.conf /etc/nginx/sites-available/parma
sudo ln -sf /etc/nginx/sites-available/parma /etc/nginx/sites-enabled/parma
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "تم التثبيت. افتح: http://$DOMAIN"
echo "لتفعيل HTTPS:"
echo "  sudo apt install -y certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d $DOMAIN"
echo ""
echo "حالة الخدمة: sudo systemctl status parma"
