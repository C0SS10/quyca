from pymongo import MongoClient
from pymongo.database import Database

from quyca.config import settings

# One client per process: it is thread-safe and already pools connections.
client: MongoClient = MongoClient(
    host=settings.MONGO_SERVER,
    port=settings.MONGO_PORT,
    username=settings.MONGO_USERNAME or None,
    password=settings.MONGO_PASSWORD.get_secret_value() or None,
)

database: Database = client[settings.MONGO_DATABASE]
calculations_database: Database = client[settings.MONGO_CALCULATIONS_DATABASE]
impactu_database: Database = client[settings.MONGO_IMPACTU_DATABASE]
