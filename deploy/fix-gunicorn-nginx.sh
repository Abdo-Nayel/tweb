#!/bin/bash
# إصلاح nginx + gunicorn.sock — شغّله من /var/www/tweb
set -euo pipefail
cd /var/www/tweb

echo "==> 1) اختبار Django مباشرة (بدون nginx)"
sudo systemctl restart tweb
sleep 3

if [ ! -S gunicorn.sock ]; then
  echo "خطأ: gunicorn.sock غير موجود!"
  sudo journalctl -u tweb -n 25 --no-pager
  sudo tail -25 /var/log/tweb/error.log 2>/dev/null || true
  exit 1
fi

ls -la gunicorn.sock
sudo chmod 660 gunicorn.sock
sudo chgrp www-data gunicorn.sock

echo "==> Django عبر socket:"
curl -sI --unix-socket gunicorn.sock http://localhost/ | head -5

echo ""
echo "==> 2) nginx — تفعيل موقع tweb فقط (بدون default_server)"
sudo cp deploy/nginx-tweb.conf /etc/nginx/sites-available/tweb
sudo ln -sf /etc/nginx/sites-available/tweb /etc/nginx/sites-enabled/tweb

# لا نمسح default بتاع مواقع تانية — tweb يشتغل بالدومين
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "==> 3) اختبار nginx بالدومين"
curl -sI -H "Host: tweb.erpbylyomastech.com" http://127.0.0.1/ | head -8

echo ""
echo "=========================================="
echo "لو Django socket رجع 200/302 — التطبيق شغال"
echo "افتح: http://tweb.erpbylyomastech.com"
echo "(curl على 127.0.0.1 بدون Host = موقع تاني على السيرفر — طبيعي 404)"
echo "=========================================="
