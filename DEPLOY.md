# SMS layihəsinin Vercel deploy-u

Bu repo Vercel-in pulsuz planında Django serverless function kimi işləmək üçün
hazırlanıb. Əsas giriş nöqtəsi `api/index.py`, Vercel konfiqurasiyası isə
`vercel.json` faylıdır.

## Vercel addımları

1. Vercel-də repo import edin.
2. Layihəni **tək** Vercel layihəsi kimi import edin: kökdəki `vercel.json`
   bütün sorğuları `api/index.py` serverless funksiyasına yönləndirir; ayrıca
   `backend` və ya `frontend` üçün ikinci servis / monorepo alt-layihəsi
   yaratmayın.
3. Framework kimi **Other** seçin. Import ekranında monorepo və ya çoxlu
   paket təklif olunarsa, root-un bu repo kökü olduğunu və yalnız bir
   deploy hədəfinin seçildiyini yoxlayın.
4. Root Directory boş qalsın, yəni layihənin kökü seçilsin.
5. Build Command dəyişməyin: `migrate` + `collectstatic` (`vercel.json`-da təyin
   olunub). `DATABASE_URL` Vercel-də build zamanı da mövcuddursa, cədvəllər hər
   deploy-da yenilənir.
6. Environment Variables bölməsinə bunları əlavə edin:
   - `DJANGO_SECRET_KEY` — uzun və gizli dəyər yazın.
   - `DJANGO_DEBUG=false`
   - **`DATABASE_URL`** — davamlı məlumat üçün PostgreSQL (aşağıda). Demo üçün
     buraxıla bilər, amma `/tmp` SQLite deploydan sonra **boşala bilər**.
   - `DJANGO_SUPERUSER_USERNAME=admin`
   - `DJANGO_SUPERUSER_PASSWORD=...`
   - `DJANGO_SUPERUSER_EMAIL=admin@example.com`
7. Deploy bitəndən sonra `/login/` səhifəsinə həmin admin istifadəçi ilə girin.

`DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` və Vercel domenləri üçün əsas
default dəyərlər artıq `settings.py` içində var. Custom domain qoşsanız,
`DJANGO_ALLOWED_HOSTS` və `CSRF_TRUSTED_ORIGINS` dəyişənlərinə həmin domeni də
əlavə edin.

## PostgreSQL (`DATABASE_URL`) — davamlı məlumat

Vercel-də `DATABASE_URL` olmadıqda layihə `/tmp/db.sqlite3` istifadə edir. Bu
fayl serverless instansiyanın diskində qalıcı deyil: yeni deploy və ya başqa
məhdudiyyət zamanı **qruplar, tələbələr və sessiyalar itə bilər**. Eyni
deploy-da belə sorğular müxtəlif funksiya instansiyalarına düşə bilər; hər
instansiyanın öz `/tmp` diski olduğundan bir sorğuda yazılan məlumat növbəti
sorğuda **boş verilənlər bazası** kimi görünə bilər. Real istifadə üçün idarə
olunan PostgreSQL tövsiyə olunur.

### Vercel Postgres (Marketplace)

1. Vercel Dashboard → layihə → **Storage** → **Create Database** → Postgres.
2. Database yaradılandan sonra **Connect** / env preview-də göstərilən
   `POSTGRES_URL` və ya tövsiyə olunan pooled connection sətirini kopyalayın.
3. Layihənin **Settings → Environment Variables** bölməsində **`DATABASE_URL`**
   təyin edin və ya Marketplace-in inject etdiyi **`POSTGRES_URL`** / **`POSTGRES_PRISMA_URL`**
   kifayətdir — `settings.py` onları avtomatik `DATABASE_URL` kimi qəbul edir.
4. **Redeploy** edin. Build mərhələsində `migrate` işləyir; ilk dəfə boş schema
   alırsınız (əvvəlki `/tmp` SQLite məlumatı köçmür).

### Provayder nümunəsi (Neon və ya Supabase)

1. Neon (https://neon.tech) və ya Supabase (https://supabase.com) hesabı ilə
   yeni PostgreSQL layihəsi / database yaradın.
2. Qoşulma sətirini kopyalayın (adətən `postgres://` və ya `postgresql://` ilə
   başlayır). Supabase/Neon bəzən `sslmode=require` parametri tələb edir; URL-də
   saxlayın.
3. Vercel → layihə → **Settings → Environment Variables** bölməsində
   `DATABASE_URL` adı ilə həmin sətri əlavə edin (bütün mühitlər üçün: Production,
   Preview, Development — ehtiyacınıza görə).
4. Yenidən deploy edin. `vercel.json` build zamanı `migrate` işlədir; əlavə
   olaraq `api/index.py` soyuq başlanğıcda da `migrate` təkrarlayır (təhlükəsiz).
5. Əvvəl `/tmp` SQLite-da olan məlumat **köçürülmür** — ilk dəfə boş schema
   alırsınız; tələbə/qrupları yenidən daxil etmək lazım ola bilər.

### Əlavə dəyişənlər (istəyə bağlı)

- `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` — öz domeniniz varsa vergüllə
  ayıraraq əlavə edin (məs. `app.example.com`).

Layihə `dj-database-url` və `psycopg2-binary` istifadə edir; əlavə Python
paketi quraşdırmaq lazım deyil.

## Köhnə demo davranışı (SQLite `/tmp`)

`DATABASE_URL` təyin etmədikdə tətbiq SQLite faylını `/tmp/db.sqlite3` kimi
yaradır və cold start zamanı migration-ları işlədir. Bu yalnız pulsuz/demo
sınaq üçündür; məlumat itkisi gözləniləndir.
