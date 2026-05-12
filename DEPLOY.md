# SMS layihəsinin Vercel deploy-u

Bu repo Vercel-in pulsuz planında Django serverless function kimi işləmək üçün
hazırlanıb. Əsas giriş nöqtəsi `api/index.py`, Vercel konfiqurasiyası isə
`vercel.json` faylıdır.

## Vercel addımları

1. Vercel-də repo import edin.
2. Framework kimi **Other** seçin.
3. Root Directory boş qalsın, yəni layihənin kökü seçilsin.
4. Build Command dəyişməyin: `python backend/manage.py collectstatic --noinput`.
5. Environment Variables bölməsinə bunları əlavə edin:
   - `DJANGO_SECRET_KEY` — uzun və gizli dəyər yazın.
   - `DJANGO_DEBUG=false`
   - `DJANGO_SUPERUSER_USERNAME=admin`
   - `DJANGO_SUPERUSER_PASSWORD=...`
   - `DJANGO_SUPERUSER_EMAIL=admin@example.com`
6. Deploy bitəndən sonra `/login/` səhifəsinə həmin admin istifadəçi ilə girin.

`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` və Vercel domenləri üçün əsas
default dəyərlər artıq `settings.py` içində var. Custom domain qoşsanız,
`DJANGO_ALLOWED_HOSTS` və `CSRF_TRUSTED_ORIGINS` dəyişənlərinə həmin domeni də
əlavə edin.

## Database qeydi

Xarici database əlavə olunmayıb. Vercel-də tətbiq SQLite faylını `/tmp/db.sqlite3`
kimi yaradır və cold start zamanı migration-ları işlədir. Bu pulsuz/demo deploy
üçün kifayətdir, amma Vercel serverless fayl sistemi daimi storage deyil:
məlumatlar deploy, cold start və ya instance dəyişəndə sıfırlana bilər.

Daimi məlumat saxlamaq lazım olsa, sonradan `DATABASE_URL` ilə PostgreSQL kimi
xarici database qoşmaq mümkündür.
