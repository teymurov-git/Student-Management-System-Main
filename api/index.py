import logging
import os
import sys
import threading
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.db import IntegrityError

BASE_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.settings import env_log_level

logging.basicConfig(
    level=logging._checkLevel(env_log_level()),
    stream=sys.stderr,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
_BOOTSTRAPPED = False
_BOOTSTRAP_ERROR = None
_BOOTSTRAP_LOCK = threading.Lock()
_BOOTSTRAP_OPTIONAL_GET_PATHS = {"/login/", "/api/health/"}


try:
    django_app = get_wsgi_application()
except Exception:
    logger.exception("Django WSGI initialization failed.")
    raise


def _prepare_sqlite_path():
    database = settings.DATABASES.get("default", {})
    if database.get("ENGINE") != "django.db.backends.sqlite3":
        return

    name = database.get("NAME")
    if not name or name == ":memory:":
        return

    Path(name).expanduser().parent.mkdir(parents=True, exist_ok=True)


def bootstrap_vercel_sqlite():
    global _BOOTSTRAPPED, _BOOTSTRAP_ERROR
    if os.environ.get("VERCEL") != "1":
        return True
    if _BOOTSTRAPPED:
        return True

    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAPPED:
            return True

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
            _BOOTSTRAP_ERROR = None
            logger.info("Vercel Django bootstrap completed.")
            return True
        except Exception as exc:
            _BOOTSTRAP_ERROR = exc
            logger.exception("Vercel Django bootstrap failed.")
            raise


def _bootstrap_can_fail_open(environ):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "")
    return method in {"GET", "HEAD"} and path in _BOOTSTRAP_OPTIONAL_GET_PATHS


def _vercel_wsgi_app(environ, start_response):
    if os.environ.get("VERCEL") == "1" and not _BOOTSTRAPPED:
        try:
            bootstrap_vercel_sqlite()
        except Exception:
            if not _bootstrap_can_fail_open(environ):
                raise
            logger.error(
                "Serving %s without completed bootstrap; see traceback above.",
                environ.get("PATH_INFO", ""),
            )

    return django_app(environ, start_response)


if os.environ.get("VERCEL") == "1":
    try:
        bootstrap_vercel_sqlite()
    except Exception:
        logger.error("Initial Vercel bootstrap failed; requests will retry it.")

app = _vercel_wsgi_app
application = _vercel_wsgi_app
