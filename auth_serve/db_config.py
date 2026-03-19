import pymysql
from dbutils.pooled_db import PooledDB
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabasePool:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DatabasePool, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, host='localhost', port=3306, user='root', password='ai15173537562',
                 database='marking_system', max_connections=10):
        if self._initialized:
            return

        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.max_connections = max_connections

        self._pool = None
        self._initialized = True
        self._create_pool()

    def _create_pool(self):
        try:
            self._pool = PooledDB(
                creator=pymysql,
                maxconnections=self.max_connections,
                mincached=2,
                maxcached=5,
                blocking=True,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database connection pool: {e}")
            raise

    def get_connection(self):
        if not self._pool:
            self._create_pool()
        return self._pool.connection()