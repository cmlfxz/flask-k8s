

from flask import Flask, render_template
from flask_migrate import Migrate
from flask_session import Session
# from flasgger import Swagger,swag_from

import logging
from logging.handlers import RotatingFileHandler
import re
import os

from .k8s import k8s
from .k8s_op import k8s_op
from .k8s_demo import k8s_demo
from .k8s_pod import k8s_pod
from .k8s_deployment import k8s_deployment
from .k8s_auth import k8s_auth
from .k8s_istio import k8s_istio
from concurrent_log_handler import ConcurrentRotatingFileHandler

from flask_cors import *
from kubernetes import client, config
# from .models import db

dir_path = os.path.dirname(os.path.abspath(__file__))
def setup_config(loglevel):
    if not os.path.exists('logs'):
        os.makedirs('logs')
    # handler = RotatingFileHandler('logs/flask.log', mode='a', maxBytes=1024 * 1024, backupCount=10, )
    handler = ConcurrentRotatingFileHandler('logs/flask.log',mode='a',maxBytes=1024*1024,backupCount=5,)
    handler.setLevel(loglevel)
    logging_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(filename)s - %(funcName)s - %(lineno)d - %(message)s')
    handler.setFormatter(logging_format)
    return handler
def create_app():
    app = Flask(__name__, instance_relative_config=True)
    # filepath = os.path.join(dir_path, 'kubeconfig')
    #生产环境要手动导入，不允许从路径导入
    filepath = os.path.join(app.instance_path, 'kubeconfig')
    config.load_kube_config(config_file=filepath)

    #  config.default(公共部分)=>config.[development|prod](环境私有部分)=>
    # [ intance/config.py(测试环境阿里云密钥,instance文件夹不能随git提交)   |   ENV(数据库账号密码，阿里云Secret)（生产环境私密部分） ]

    # 公共部分配置 config/default.py
    app.config.from_object('config.default')

    try:
        env = os.environ["ENV"]
        object = ""
        if re.match(r'dev', env, re.M | re.I):
            object = "config.development"
        elif re.match(r'test', env, re.M | re.I):
            object = "config.test"
        elif re.match(r'prod', env, re.M | re.I):
            object = "config.production"
        else:
            app.logger.error("客观，您输入的环境变量ENV有误，本店要打烊了")
            os.exit(-1)
        app.logger.info("即将加载的配置是:{}".format(object))

        # 各个环境独立的部分
        app.config.from_object(object)

        # 测试从instance下config.py去读取私密信息
        if re.match(r'dev', env, re.M | re.I):
            # 加载阿里云密钥 instance/config.py
            # app.config.from_pyfile('config.py')
            # access_id=app.config.get('ACCESS_ID')
            # access_secret=app.config.get('ACCESS_SECRET')
            # app.logger.info("测试环境 access_id:{},  access_secret:{}".format(access_id,access_secret))
            pass

        # 生产环境，要从环境变量加载私密信息，不再从instance下config.py去读取
        if re.match(r'prod', env, re.M | re.I):
            try:
                # access_id=os.environ["ACCESS_ID"].strip("\'").replace("\n","")
                # access_secret=os.environ["ACCESS_SECRET"].strip("\'").replace("\n","")
                # app.logger.info("生产环境 access_id:{},access_secret:{}".format(access_id,access_secret))

                # app.config['ACCESS_ID'] = access_id
                # app.config['ACCESS_SECRET'] = access_secret

                MYSQL_USERNAME = os.environ["MYSQL_USERNAME"].strip("\'").replace("\n", "")
                MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"].strip("\'").replace("\n", "")
                # REDIS_PASSWORD=str(os.environ["REDIS_PASSWORD"]).strip("\'")

                app.config['MYSQL_USERNAME'] = MYSQL_USERNAME
                app.config['MYSQL_PASSWORD'] = MYSQL_PASSWORD
                # app.config['REDIS_PASSWORD'] = REDIS_PASSWORD

                app.logger.info("生产环境 数据库账号:{},密码：{}".format(MYSQL_USERNAME, MYSQL_PASSWORD))
                DIALECT = str(app.config.get('DIALECT'))
                MYSQL_DRIVER = str(app.config.get('MYSQL_DRIVER'))
                MYSQL_HOST = str(app.config.get('MYSQL_HOST'))
                MYSQL_PORT = app.config.get('MYSQL_PORT')
                MYSQL_DATABASE = str(app.config.get('MYSQL_DATABASE'))
                sqlstring = '{}+{}://{}:{}@{}:{}/{}?charset=utf8'. \
                    format(DIALECT, MYSQL_DRIVER, MYSQL_USERNAME, MYSQL_PASSWORD, MYSQL_HOST, MYSQL_PORT,
                           MYSQL_DATABASE).replace("\n", "")
                app.config['SQLALCHEMY_DATABASE_URI'] = sqlstring

                app.logger.info(app.config.get('SQLALCHEMY_DATABASE_URI'))
            except Exception as e:
                app.logger.error("无法从环境变量获取到信息，请检查secrets.yaml,{}".format(e))
            # app.config.from_pyfile('config.py')

    except KeyError as e:
        app.logger.info("获取不到环境变量:{}".format(e))
        app.config.from_object("config.development")

        # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    Session(app)
    # Swagger(app)
    # r'/*' 是通配符，让本服务器所有的URL 都允许跨域请求
    CORS(app, supports_credentials=True,resources=r'/*')
    # CORS(app, supports_credentials=True,resources=r'/*',methods='GET,POST,OPTIONS',allow_headers="cluster_name,x-requested-with,content-type")

    # # app初始化
    # db.init_app(app)
    # 日志初始化
    try:
        loglevel = app.config.get('LOG_LEVEL')
    except:
        loglevel = logging.WARNING
    handler = setup_config(loglevel)
    app.logger.addHandler(handler)

    # # 绑定数据库
    # migrate = Migrate()
    # migrate.init_app(app, db)

    # 加载蓝图
    app.register_blueprint(k8s)
    app.register_blueprint(k8s_op)
    app.register_blueprint(k8s_demo)
    app.register_blueprint(k8s_deployment)
    app.register_blueprint(k8s_pod)
    app.register_blueprint(k8s_auth)
    app.register_blueprint(k8s_istio)
    # app.add_url_rule('/',endpoint='index')

    # 调试信息
    app.logger.info(app.url_map)
    # app.logger.info(auth.root_path)
    return app
