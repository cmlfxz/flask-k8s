import json
from datetime import date, datetime
import decimal
import pymysql 
from flask import current_app
import base64

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)

class JsonUtil:
    
    def __default(self,obj):      
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')        
        else:
            raise TypeError('%r is not JSON serializable' % obj)

      
    def parseJsonObj(self,obj):
        jsonstr=json.dumps(obj,default=self.__default,ensure_ascii=False) #cls=DecimalEncoder
        return jsonstr
    
    def parseJsonString(self,jsonstring):
        obj=json.loads(jsonstring)
        return obj


        
def get_db_conn():
    conn = None
    try:
        mysql_host = current_app.config.get('MYSQL_HOST')
        mysql_port = int(current_app.config.get('MYSQL_PORT'))
        mysql_username = current_app.config.get('MYSQL_USERNAME')
        mysql_password = current_app.config.get('MYSQL_PASSWORD')
        mysql_database = current_app.config.get('MYSQL_DATABASE')  
        conn = pymysql.connect(host=mysql_host, port=mysql_port, user=mysql_username,password=mysql_password,
            db=mysql_database,charset='utf8')
        # dbinfo = db_info(mysql_host,mysql_port,mysql_username,mysql_password,mysql_database)
    except Exception as e:
        error = "数据库地址获取失败:{}".format(e)
        current_app.logger.error(error)
    return conn

def my_encode(a):
    return base64.b64encode(a.encode('utf-8')) 

def my_decode(a):
    return base64.b64decode(a).decode("utf-8")

def str_to_int(str):    
    # return str=="" ? 1 : int(str)  
    return 1 if str=="" else int(str)

def str_to_float(str):    
    return 1 if str=="" else float(str)


import threading
from DBUtils.PooledDB import PooledDB

class SingletonDBPool(object):
    _instance_lock = threading.Lock()

    def __init__(self):
        print("单例数据库连接初始化")
        mysql_host = current_app.config.get('MYSQL_HOST')
        mysql_port = int(current_app.config.get('MYSQL_PORT'))
        mysql_username = current_app.config.get('MYSQL_USERNAME')
        mysql_password = current_app.config.get('MYSQL_PASSWORD')
        mysql_database = current_app.config.get('MYSQL_DATABASE')
        self.pool = PooledDB(creator=pymysql,
                             maxconnections=50,
                             mincached=2,
                             maxcached=5,
                             maxshared=3,
                             blocking=True,
                             maxusage=None,
                             setsession=[],
                             ping=0,
                             host=mysql_host,
                             port=mysql_port,
                             user=mysql_username,
                             password=mysql_password,
                             database=mysql_database,
                             charset='utf8')

    def __new__(cls, *args, **kwargs):
        if not hasattr(SingletonDBPool, "_instance"):
            with SingletonDBPool._instance_lock:
                if not hasattr(SingletonDBPool, "_instance"):
                    SingletonDBPool._instance = object.__new__(cls, *args, **kwargs)
        return SingletonDBPool._instance
    # def __new__(cls,*args,**kwargs):
    #     if not hasattr(SingletonDBPool, "_instance"):
    #         SingletonDBPool._instance = object.__new__(cls, *args, **kwargs)
    #     return SingletonDBPool._instance

    def connect(self):
        return self.pool.connection()