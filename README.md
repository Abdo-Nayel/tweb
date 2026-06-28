# LyomasPhone

نظام إدارة محل تليفونات احترافي — متعدد الفروع والعملات.

## المميزات

- إدارة مخزون أجهزة وإكسسوارات (ماركات، موديلات، سيريال/IMEI، ضمان)
- نقطة بيع (POS) مع باركود
- مشتريات ومبيعات ومرتجعات
- عملاء وموردين وخزينة
- تقارير مخزون وأرباح وضمان
- واجهة عربية بالكامل — العملة بالجنيه المصري (ج.م)

## التشغيل السريع

```bash
pip install -r Requirements.txt
python manage.py migrate
python manage.py setup_shop --username admin --password admin123 --shop-name "محل التليفونات"
python manage.py runserver
```

افتح: http://127.0.0.1:8000

## الإنتاج (tweb.erpbylyomastech.com)

**دليل كامل:** [`deploy/TWEB.md`](deploy/TWEB.md)

```bash
# 1) DNS: A → tweb → 162.0.237.222
# 2) على السيرفر:
DB_PASSWORD='كلمة-postgres-قوية' bash deploy/install-tweb.sh
# 3) HTTPS:
CERTBOT_EMAIL='your@email.com' bash deploy/enable-ssl-tweb.sh
```
