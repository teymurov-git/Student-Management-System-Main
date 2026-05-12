# SMS layihəsinin yerləşdirilməsi (DEPLOY)

Əsas tətbiq **Django**: server tərəfində HTML, sessiya və API (`/api`). **Vercel** bu arxitekturada ənənəvi Django hostu deyil; istehsalat üçün **bir Python prosesi** ( məsələn Render, Railway və ya Fly.io ) istifadə edin.

## İstehsalat: Django (Render / Railway / Fly)

1. **Kök layihə qovluğu:** `backend/` ( və ya layihənin build addımı ilə eyni qovluğu seçin ).
2. **Başlatma:** `backend/Procfile`-də nümunə: `web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
3. **Əsas environment dəyişənləri:**
   - `DJANGO_DEBUG=false`
   - `DJANGO_SECRET_KEY`
   - `DJANGO_ALLOWED_HOSTS` — domeniniz ( vergüllə ayrılmış )
   - `DATABASE_URL` — PostgreSQL ( `django-environ` / `dj-database-url` kimi parse olunmalıdır )
   - `CSRF_TRUSTED_ORIGINS` — tam HTTPS mənşə ( məs.: `https://app.example.com` )
   - Statika üçün istehsalat axınına `collectstatic` əlavə edin

Əlavə detallar üçün repodakı `README.md`.

## Vercel ( istəyə bağlı ): statik landing

Panel Django-da qalır. Yalnız sadə statik qarşılama üçün:

1. `public/index.html` nümunə kimi verilib.
2. Vercel-də Framework **Other**, **Output Directory**: `public` ( layihənin root parametrlərindən asılı olaraq uyğunlaşdırın ).

Layihənin kökündəki `vercel.json` nümunədə `buildCommand`: `exit 0` ilə boş build saxlanılır; Vercel interfeysində bu addımı sıfırlamaq də olar.

**Next.js tam SPA yenidən əlavə etməyin** — əsas UI Django portalındadır.
