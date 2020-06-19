import  os
import logging
from redis import Redis

SECRET_KEY = b'feaf0ca3870de645'

REDIS_HOST='192.168.11.200'
REDIS_PORT=6689
SESSION_REDIS =  Redis(host=REDIS_HOST,port=REDIS_PORT)

DIALECT = 'mysql'
MYSQL_DRIVER = 'pymysql'
MYSQL_USERNAME = 'dev_user'
MYSQL_PASSWORD = 'abc123456'
MYSQL_HOST = '192.168.11.200'
MYSQL_PORT = '52100'
MYSQL_DATABASE = 'tutorial'

# # SQLALCHEMY_DATABASE_URI ="mysql+pymysql://dev_user:abc123456@192.168.11.200:52100/flask-tutorial?charset=utf8"
SQLALCHEMY_DATABASE_URI = '{}+{}://{}:{}@{}:{}/{}?charset=utf8'.format(
    DIALECT,MYSQL_DRIVER,MYSQL_USERNAME,MYSQL_PASSWORD,MYSQL_HOST,MYSQL_PORT,MYSQL_DATABASE
)

LOG_LEVEL = logging.DEBUG

