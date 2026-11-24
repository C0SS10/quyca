from flask import Blueprint, Response, current_app

docs_router = Blueprint("docs", __name__)

# Crawlers look for these files at the root, so they are served there instead of redirecting to /static.
GOOGLE_SITE_VERIFICATION_FILE = "google54c758d287263571.html"


@docs_router.route("/robots.txt", methods=["GET"])
def get_robots() -> Response:
    return current_app.send_static_file("robots.txt")


@docs_router.route(f"/{GOOGLE_SITE_VERIFICATION_FILE}", methods=["GET"])
def get_google_site_verification() -> Response:
    return current_app.send_static_file(GOOGLE_SITE_VERIFICATION_FILE)
