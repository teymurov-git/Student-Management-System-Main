# Telebe Idareetme Sistemi (SMS)

Bu layihe Django esasli telebe idareetme panelidir. Interfeys server terefinde
Django sablonlari ile isleyir, `/api/` endpoint-leri ise JWT ile inteqrasiyalar
ucun saxlanilib.

## Lokal ishe salma

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Brauzer: `http://127.0.0.1:8000/`

Admin: `http://127.0.0.1:8000/admin/`

## Vercel deploy

Layihe Vercel-in pulsuz planinda Django serverless function kimi deploy olunmaq
ucun hazirlanib. Esas fayllar:

- `api/index.py` - Vercel WSGI giris noqtesi.
- `vercel.json` - Django function route ve `collectstatic` build addimi.
- `requirements.txt` - Vercel-in root-dan Python paketlerini tapmasi ucun.

Vercel-de repo import edin, Framework olaraq **Other** secin ve environment
deyishenlerini elave edin:

- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG=false`
- **`DATABASE_URL`** — real istifade ucun **vacibdir** (PostgreSQL, məs. Neon və ya
  Supabase). Təyin olunmayanda Vercel `/tmp/db.sqlite3` istifadə edir; deploy və
  soyuq başlanğıcdan sonra məlumat itə bilər.
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_PASSWORD`
- `DJANGO_SUPERUSER_EMAIL`

Etrafli addimlar `DEPLOY.md` faylindadir.

## Database qeydi

Lokal inkişaf üçün layihə `backend/db.sqlite3` (SQLite) ilə işləyir; bu faylı
git-ə əlavə etməyin.

**Vercel / production:** serverless mühitdə fayl sistemi daimi deyil. `DATABASE_URL`
təyin edilmədikdə tətbiq avtomatik olaraq `/tmp` altında SQLite yaradır — həmin
fayl deploy, cold start və ya instance dəyişəndə **silinə və ya boş ola bilər**.
Davamlı məlumat üçün `DATABASE_URL` ilə idarə olunan PostgreSQL qoşun; paketlər
artıq `dj-database-url` və `psycopg2-binary` ilə uyğundur. Ətraflı siyahı və
addımlar üçün `DEPLOY.md`-ə baxın.

## Faydali URL-ler

- Portal: `/`
- Login: `/login/`
- Admin: `/admin/`
- API token: `POST /api/auth/token/`
- Export: `/export/students.xlsx`, `/export/students.pdf`, `/export/payments.xlsx`
