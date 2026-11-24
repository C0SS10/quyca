from elasticsearch import Elasticsearch

from quyca.config import settings

es_database: Elasticsearch = Elasticsearch(
    settings.ES_SERVER,
    basic_auth=(settings.ES_USERNAME, settings.ES_PASSWORD.get_secret_value()),
)
