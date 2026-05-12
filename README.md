<<<<<<< HEAD
# Student-Management-System-Main
=======
# Tələbə İdarəetmə Sistemi (SMS)



**İnterfeys:** Django — server tərəfində şablonlar (`portal`), sessiya ilə giriş, formlar, export. Kök URL: `/`.



**REST API** (`/api/…`, JWT) istəyə bağlıdır — xarici skriptlər və inteqrasiya üçün saxlanılır.



## Struktur (Python)



| Qovluq | Təsvir |

|--------|--------|

| `backend/portal/` | Veb MVC: görünüşlər, şablonlar, formlar, export |

| `backend/students/`, `payments/`, `attendance/`, `exams/`, `audit/` | Modellər + DRF API |



## Lokal işə salma



```powershell

cd backend

python -m venv .venv

.\.venv\Scripts\activate

pip install -r requirements.txt

python manage.py migrate

python manage.py createsuperuser

python manage.py runserver

```



Brauzer: **http://127.0.0.1:8000/** — `/login/` (eyni superuser).



Admin: **http://127.0.0.1:8000/admin/**



İstehsalatda statika: `python manage.py collectstatic`.



## Deploy (Django tək proses)



Ətraflı: [**DEPLOY.md**](./DEPLOY.md).



Qısa göstərişlər:



- **Host:** Render, Railway, Fly və s. — `backend/` üçün root; start: `gunicorn` (**`backend/Procfile`**).

- **Environment:** `DJANGO_DEBUG=false`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DATABASE_URL`, `CSRF_TRUSTED_ORIGINS` (HTTPS domen).

- **`CORS_ALLOWED_ORIGINS`** — yalnız `/api`-ə başqa bir domendə olan klient Qoşsanız lazımdır.



### API (istəyə bağlı)



| Endpoint | Təsvir |

|----------|--------|

| `POST /api/auth/token/` | JWT |

| `GET /api/students/` … | DRF resursları |



Portal export (giriş tələb olunur): `/export/students.xlsx`, `/export/students.pdf`, `/export/payments.xlsx`.



## Texniki qeyd



Ödəniş və sınaq tarixçəsi saxlanılır; portal əməliyyatları `audit` cədvəlinə yazılır.


>>>>>>> b8a8dc8 ('updated')
