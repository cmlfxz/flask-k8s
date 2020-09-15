from flask import Blueprint
from flask_cors import *

# 定义蓝图
config = Blueprint('config',__name__,url_prefix='/api/k8s/config')
CORS(config, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.config import views