import os
import sys
from pathlib import Path

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.db import IntegrityError

BASE_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = get_wsgi_application()
application = app


def bootstrap_vercel_sqlite():
    if os.environ.get("VERCEL") != "1":
        return

    call_command("migrate", interactive=False, verbosity=0)

    username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
    password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
    email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
    if not username or not password:
        return

    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    if user_model.objects.filter(username=username).exists():
        return

    try:
        user_model.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
    except IntegrityError:
        pass


bootstrap_vercel_sqlite()
