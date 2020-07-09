import os,json
from datetime import date, datetime
import decimal
import pymysql 
from flask import current_app
import base64
import threading
import pytz
from DBUtils.PooledDB import PooledDB

dir_path = os.path.dirname(os.path.abspath(__file__))

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

# 处理接收的json数据，如果前端传的不是整形数据，进一步转化需要再调用str_to_int()
def handle_input(obj):
    # print("{}数据类型{}".format(obj,type(obj)))
    if obj == None or obj=='null':
        return None
    elif isinstance(obj,str):
        return (obj.strip())
    elif isinstance(obj,int):
        return obj
    elif isinstance(obj,dict):
        return obj
    elif isinstance(obj,list):
        return obj
    else:
        print("未处理类型{}".format(type(obj)))
        return(obj.strip())

def handle_toleraion_seconds(toleration):
    print(toleration)
    if toleration == "" or toleration == 'null':
        return None
    else:
        return int(toleration)

def string_to_int(string):
    print(string)
    if string == "" or string == 'null' or string== None:
        return None
    else:
        return int(string)
def handle_toleration_item(item):
    print(item)
    if item == "" or item == 'null':
        return None
    else:
        return item
    
def simple_error_handle(msg):
    return jsonify({"error":msg})


#参数是datetime
def time_to_string(dt):
    tz_sh = pytz.timezone('Asia/Shanghai')
    return dt.astimezone(tz_sh).strftime("%Y-%m-%d")
    # return  dt.astimezone(tz_sh).strftime("%Y-%m-%d %H:%M:%S")

def utc_to_local(utc_time_str, utc_format='%Y-%m-%dT%H:%M:%S.%fZ'):
    local_tz = pytz.timezone('Asia/Shanghai')
    local_format = "%Y-%m-%d %H:%M:%S"
    utc_dt = datetime.strptime(utc_time_str, utc_format)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    time_str = local_dt.strftime(local_format)
    return time_str

class SingletonDBPool(object):
    _instance_lock = threading.Lock()

    def __init__(self):
        # print("单例数据库连接初始化")
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

    def connect(self):
        return self.pool.connection()