from datetime import date, datetime
import decimal
import pymysql 
from flask import jsonify,current_app,make_response
import base64
import threading
import json,os,math,requests,time,pytz,ssl,yaml
from DBUtils.PooledDB import PooledDB



import logging
from jaeger_client import Config
from flask_opentracing import FlaskTracer
from flask import _request_ctx_stack as stack
from jaeger_client import Tracer,ConstSampler
from jaeger_client import Tracer, ConstSampler
from jaeger_client.reporter import NullReporter
from jaeger_client.codecs import B3Codec
from opentracing.ext import tags
from opentracing.propagation import Format
from opentracing_instrumentation.request_context import get_current_span,span_in_context

def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)
    config = Config(
        config={
            'sampler': {
                'type': 'const',
                'param': 1,
            },
            # 'local_agent': {
            #     'reporting_host': '192.168.11.142',
            #     'reporting_port': '6831',
            # },
            'local_agent': {
                'reporting_host': 'zipkin.istio-system',
                'reporting_port': '9411',
            },
            'logging': True,
            # zipkin使用b3
            'propagation': 'b3',
        },
        service_name=service,
    )
    # this call also sets opentracing.tracer
    return config.initialize_tracer()

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

# 处理接收的json数据
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

#deployment 处理weight还在用
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
# 返回m为单位的cpu值
def handle_cpu(cpu):
    if cpu == "0":
        return 0
    elif cpu.endswith('m'):
        return int(cpu.split('m')[0])
    elif cpu.endswith('n'):
        # 返回m为单位的cpu值
        # return int(cpu.split('n')[0])/1000/1000
        return math.ceil(int(cpu.split('n')[0])/1000/1000)
    else:
        print("出现未识别的CPU格式{}".format(cpu))
        return 0

def handle_disk_space(disk):
    if disk == "0":
        return 0
    elif disk.endswith('Ki'):
        # 转成G单位大小
        return math.ceil(int(disk.split('Ki')[0])/1024/1024)
    elif disk.endswith('Mi'):
        return math.ceil(int(disk.split('Mi')[0])/1024)
    else:
        print("出现未识别的disk_space格式{}".format(disk))
        return 0

def handle_memory(memory):
    if memory == "0":
        return 0
    elif memory.endswith('Ki'):
        return math.ceil(int(memory.split('Ki')[0])/1024)
    elif memory.endswith('Mi'):
        return math.ceil(int(memory.split('Mi')[0]))
    else:
        print("出现未识别的内存格式{}".format(memory))
        return 0

def simple_error_handle(msg):
    return make_response(jsonify({"error":msg}),1000)
    # return jsonify({"error":msg})

def error_with_status(error=None,msg=None,status=None):
    return make_response(jsonify({"error":error,"msg":msg}),status)
#参数是datetime
def time_to_string(dt):
    #修复bug
    if dt == None:
        return None
    tz_sh = pytz.timezone('Asia/Shanghai')
    # return dt.astimezone(tz_sh).strftime("%Y-%m-%d")
    return  dt.astimezone(tz_sh).strftime("%Y-%m-%d %H:%M:%S")

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

def get_cluster_config(cluster_name):
    cluster_config = None
    # conn = get_db_conn()
    pool = SingletonDBPool()
    conn = pool.connect()
    if conn == None:
        print("无法获取数据库连接")
    else:
        cursor = conn.cursor()
        sql = "select cluster_config from cluster where cluster_name = \'{}\' ".format(cluster_name)
        try:
            cursor.execute(sql)
            results  =  cursor.fetchone()
            cluster_config = results[0]
        except Exception as e:
            print("查询不到数据")
    conn.close()
    return cluster_config

