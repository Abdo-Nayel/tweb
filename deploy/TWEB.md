# نشر LyomasPhone على tweb.erpbylyomastech.com

## المتطلبات

| البند | القيمة |
|--------|--------|
| السيرفر | Ubuntu (نفس سيرفر pweb) |
| IP | `162.0.237.222` |
| الدومين | `tweb.erpbylyomastech.com` |
| المستخدم | `softwarehouse` (مع sudo) |
| المسار | `/var/www/tweb` |
| الخدمة | `tweb.service` |

## 1) DNS (مهم — قبل التثبيت)

في لوحة الدومين أضف:

```
Type: A
Name: tweb
Value: 162.0.237.222
TTL: 300
```

تحقق (من أي جهاز):

```bash
nslookup tweb.erpbylyomastech.com
```

## 2) رفع الكود على GitHub

المستودع: [github.com/Abdo-Nayel/tweb](https://github.com/Abdo-Nayel/tweb)

من جهاز التطوير:

```bash
git remote add tweb https://github.com/Abdo-Nayel/tweb.git   # مرة واحدة
git add -A
git commit -m "LyomasPhone — initial tweb release"
git push -u tweb main
```

## 3) التثبيت على السيرفر

```bash
ssh softwarehouse@162.0.237.222

# تثبيت أول مرة
git clone https://github.com/Abdo-Nayel/tweb.git /var/www/tweb
cd /var/www/tweb
chmod +x deploy/*.sh

DB_PASSWORD='ضع-كلمة-postgres-قوية' \
SHOP_NAME='اسم محلك' \
bash deploy/install-tweb.sh
```

**أو** لو المجلد موجود:

```bash
cd /var/www/tweb
git pull origin main
DB_PASSWORD='...' bash deploy/install-tweb.sh
```

## 4) HTTPS

```bash
cd /var/www/tweb
CERTBOT_EMAIL='your@email.com' bash deploy/enable-ssl-tweb.sh
```

## 5) الدخول

- الرابط: https://tweb.erpbylyomastech.com
- المستخدم الافتراضي: `admin`
- كلمة المرور: `admin123` — **غيّرها فوراً**

## 6) تحديث لاحق

```bash
cd /var/www/tweb
bash deploy/update-tweb.sh
```

## أوامر مفيدة

```bash
sudo systemctl status tweb
sudo journalctl -u tweb -f
sudo tail -f /var/log/tweb/error.log
sudo nginx -t && sudo systemctl reload nginx
```

## ملفات `.env` (مرجع)

انظر `deploy/.env.example`
