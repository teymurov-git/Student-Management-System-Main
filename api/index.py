import logging
import os
import sys
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.db import IntegrityError

BASE_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

logger = logging.getLogger(__name__)
_BOOTSTRAPPED = False

app = get_wsgi_application()
application = app


def _prepare_sqlite_path():
    database = settings.DATABASES.get("default", {})
    if database.get("ENGINE") != "django.db.backends.sqlite3":
        return

    name = database.get("NAME")
    if not name or name == ":memory:":
        return

    Path(name).expanduser().parent.mkdir(parents=True, exist_ok=True)


def bootstrap_vercel_sqlite():
    global _BOOTSTRAPPED
    if os.environ.get("VERCEL") != "1":
        return
    if _BOOTSTRAPPED:
        return

    try:
        _prepare_sqlite_path()
        call_command("migrate", interactive=False, verbosity=1)

        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "")
        if username and password:
            from django.contrib.auth import get_user_model

            user_model = get_user_model()
            if not user_model.objects.filter(username=username).exists():
                try:
                    user_model.objects.create_superuser(
                        username=username,
                        email=email,
                        password=password,
                    )
                except IntegrityError:
                    pass

        _BOOTSTRAPPED = True
    except Exception:
        logger.exception("Vercel Django bootstrap failed before serving requests.")
        raise


bootstrap_vercel_sqlite()
