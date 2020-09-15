from flask import Blueprint
from flask_cors import *

# 定义蓝图
service = Blueprint('service',__name__,url_prefix='/api/k8s/service')
CORS(service, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.service import views