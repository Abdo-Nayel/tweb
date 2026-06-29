#!/bin/bash
# حل 404 — TCP port 8010 بدل unix socket + nginx للدومين
set -euo pipefail
cd /var/www/tweb

echo "==> 1) Gunicorn على port 8010"
sudo cp deploy/tweb.service /etc/systemd/system/tweb.service
sudo systemctl daemon-reload
sudo systemctl restart tweb
sleep 3
sudo systemctl is-active tweb

echo "==> 2) اختبار Django مباشرة"
curl -sI http://127.0.0.1:8010/ | head -6

echo ""
echo "==> 3) nginx"
sudo cp deploy/nginx-tweb.conf /etc/nginx/sites-available/tweb
sudo ln -sf /etc/nginx/sites-available/tweb /etc/nginx/sites-enabled/tweb
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "==> 4) اختبار عبر nginx + Host"
curl -sI -H "Host: tweb.erpbylyomastech.com" http://127.0.0.1/ | head -8

echo ""
echo "==> 5) المواقع المفعّلة"
ls -la /etc/nginx/sites-enabled/

echo ""
echo "=========================================="
echo "لو خطوة 2 رجعت 200/302 → Django شغال"
echo "لو خطوة 4 رجعت 404 → nginx مش موجه للدومين"
echo "  تحقق DNS: dig tweb.erpbylyomastech.com +short"
echo "افتح: http://tweb.erpbylyomastech.com"
echo "admin / admin123"
echo "=========================================="
