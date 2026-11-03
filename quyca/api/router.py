from flask import Blueprint

from quyca.api.affiliation_router import affiliation_router
from quyca.api.apc_router import apc_router
from quyca.api.completer_router import completer_router
from quyca.api.docs_router import docs_router
from quyca.api.geo_router import geo_router
from quyca.api.info_router import info_router
from quyca.api.patent_router import patent_router
from quyca.api.person_router import person_router
from quyca.api.ping_router import ping_router
from quyca.api.project_router import project_router
from quyca.api.search_router import search_router
from quyca.api.source_router import source_router
from quyca.api.submit_router import submit_router
from quyca.api.user_auth_router import user_auth_router
from quyca.api.user_crud_router import user_crud_router
from quyca.api.work_router import work_router
from quyca.api.me_router import me_router

router = Blueprint("router", __name__)

router.register_blueprint(search_router, url_prefix="/search")
router.register_blueprint(affiliation_router, url_prefix="/affiliation")
router.register_blueprint(person_router, url_prefix="/person")
router.register_blueprint(source_router, url_prefix="/source")
router.register_blueprint(work_router, url_prefix="/work")
router.register_blueprint(patent_router, url_prefix="/patent")
router.register_blueprint(project_router, url_prefix="/project")
router.register_blueprint(geo_router, url_prefix="/geo")
router.register_blueprint(apc_router, url_prefix="/apc")
router.register_blueprint(completer_router, url_prefix="/completer")
router.register_blueprint(user_auth_router)
router.register_blueprint(me_router)
router.register_blueprint(user_crud_router)
router.register_blueprint(submit_router, url_prefix="/submit")

router.register_blueprint(info_router)
router.register_blueprint(ping_router)
router.register_blueprint(docs_router)
