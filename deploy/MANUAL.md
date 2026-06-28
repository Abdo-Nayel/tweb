# رفع يدوي — LyomasPhone على السيرفر

## الطريقة 1: من GitHub (أسهل)

```bash
ssh softwarehouse@162.0.237.222

sudo rm -rf /var/www/tweb
sudo mkdir -p /var/www/tweb /var/log/tweb
sudo chown -R softwarehouse:www-data /var/www/tweb /var/log/tweb

git clone https://github.com/Abdo-Nayel/tweb.git /var/www/tweb
cd /var/www/tweb
chmod +x deploy/*.sh

# كلمة سر DB — غيّرها لو حابب
DB_PASSWORD='Lyo22999' bash deploy/manual-fix.sh
```

---

## الطريقة 2: رفع ZIP من Windows (بدون git)

### على جهازك (PowerShell)

```powershell
cd E:\LyomasPhone

# اضغط المشروع (بدون venv و db)
Compress-Archive -Path apps,config,deploy,manage.py,Requirements.txt,static,templates,README.md -DestinationPath tweb-upload.zip -Force
```

### ارفع الملف

```powershell
scp tweb-upload.zip softwarehouse@162.0.237.222:~/
```

### على السيرفر

```bash
ssh softwarehouse@162.0.237.222

sudo rm -rf /var/www/tweb
sudo mkdir -p /var/www/tweb /var/log/tweb
sudo chown -R softwarehouse:www-data /var/www/tweb /var/log/tweb

unzip -o ~/tweb-upload.zip -d /var/www/tweb
cd /var/www/tweb
chmod +x deploy/*.sh

DB_PASSWORD='Lyo22999' bash deploy/manual-fix.sh
```

---

## بعد التثبيت

| الرابط | |
|--------|--|
| http://162.0.237.222 | يشتغل مباشرة |
| http://tweb.erpbylyomastech.com | يحتاج DNS |

**الدخول:** `admin` / `admin123`

---

## HTTPS (بعد ما HTTP يشتغل)

```bash
sudo certbot --nginx -d tweb.erpbylyomastech.com
```

ثم ضيّق `.env`:

```env
DJANGO_ALLOWED_HOSTS=tweb.erpbylyomastech.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://tweb.erpbylyomastech.com
DJANGO_SESSION_COOKIE_SECURE=True
DJANGO_CSRF_COOKIE_SECURE=True
```

```bash
sudo systemctl restart tweb
```

---

## لو في مشكلة

```bash
sudo systemctl status tweb
sudo journalctl -u tweb -n 30 --no-pager
sudo tail -20 /var/log/nginx/error.log
curl -I http://127.0.0.1/
ls -la /var/www/tweb/gunicorn.sock
```
