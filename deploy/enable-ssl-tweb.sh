#!/bin/bash
# تفعيل HTTPS لـ tweb.erpbylyomastech.com (بعد DNS + nginx)
set -euo pipefail

DOMAIN="tweb.erpbylyomastech.com"
APP_DIR="/var/www/tweb"
EMAIL="${CERTBOT_EMAIL:-admin@erpbylyomastech.com}"

echo "==> certbot"
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect

echo "==> تحديث .env للـ HTTPS"
cd "$APP_DIR"
if grep -q 'DJANGO_SESSION_COOKIE_SECURE=False' .env 2>/dev/null; then
  sed -i 's/DJANGO_SESSION_COOKIE_SECURE=False/DJANGO_SESSION_COOKIE_SECURE=True/' .env
  sed -i 's/DJANGO_CSRF_COOKIE_SECURE=False/DJANGO_CSRF_COOKIE_SECURE=True/' .env
fi
if ! grep -q "https://${DOMAIN}" .env; then
  sed -i "s|DJANGO_CSRF_TRUSTED_ORIGINS=.*|DJANGO_CSRF_TRUSTED_ORIGINS=https://${DOMAIN}|" .env
fi

sudo systemctl restart tweb
echo "تم — https://${DOMAIN}"
