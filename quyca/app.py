import sentry_sdk
from flask import Flask
from flask_compress import Compress
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from sentry_sdk.integrations.flask import FlaskIntegration

from quyca.api.router import router
from quyca.config import settings


def create_app() -> Flask:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN or None,
        environment=settings.ENVIRONMENT,
        release=settings.APP_VERSION,
        integrations=[FlaskIntegration()],
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
    )

    app = Flask(__name__)
    app.config.update(
        JWT_SECRET_KEY=settings.JWT_SECRET_KEY.get_secret_value(),
        JWT_ACCESS_TOKEN_EXPIRES=settings.JWT_ACCESS_TOKEN_EXPIRES,
        JWT_TOKEN_LOCATION=["cookies"],
        JWT_ACCESS_COOKIE_NAME="access_token_cookie",
        JWT_ACCESS_COOKIE_PATH="/",
        JWT_COOKIE_DOMAIN=settings.JWT_COOKIE_DOMAIN or None,
        JWT_COOKIE_HTTPONLY=True,
        JWT_COOKIE_SAMESITE="None",
        JWT_COOKIE_SECURE=True,
        JWT_COOKIE_CSRF_PROTECT=True,
        JWT_CSRF_IN_COOKIES=True,
        LOCAL_STORAGE_PATH=settings.LOCAL_STORAGE_PATH,
        GOOGLE_CREDENTIALS=settings.GOOGLE_CREDENTIALS,
        GOOGLE_PARENT_ID=settings.GOOGLE_PARENT_ID,
    )

    JWTManager(app)
    CORS(app, supports_credentials=True, origins=settings.CORS_ORIGINS)
    Compress(app)
    app.register_blueprint(router, url_prefix=settings.API_URL_PREFIX)
    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=settings.APP_PORT, debug=settings.APP_DEBUG, threaded=True)
