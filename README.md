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
- `DJANGO_SUPERUSER_USERNAME`
- `DJANGO_SUPERUSER_PASSWORD`
- `DJANGO_SUPERUSER_EMAIL`

Etrafli addimlar `DEPLOY.md` faylindadir.

## Database qeydi

Xarici database teleb olunmur. Lokal muhitde `backend/db.sqlite3`, Vercel-de ise
`/tmp/db.sqlite3` SQLite fayli istifade olunur. Vercel serverless storage daimi
olmadigi ucun deploy ve cold start zamani melumatlar sifirlana biler; bu qurulus
pulsuz/demo istifade ucundur.

## Faydali URL-ler

- Portal: `/`
- Login: `/login/`
- Admin: `/admin/`
- API token: `POST /api/auth/token/`
- Export: `/export/students.xlsx`, `/export/students.pdf`, `/export/payments.xlsx`
