from quyca.config import settings
from quyca.constants.banner import BANNER

# Loaded automatically by gunicorn from the working directory (/app in the containers).
wsgi_app = "quyca.app:create_app()"
bind = f"0.0.0.0:{settings.APP_PORT}"
workers = settings.GUNICORN_WORKERS
timeout = settings.GUNICORN_TIMEOUT
reload = settings.APP_DEBUG
accesslog = "-"
errorlog = "-"


def when_ready(server: object) -> None:
    """Runs once in the master process when it starts listening (not per worker or reload)."""
    print(BANNER, flush=True)
