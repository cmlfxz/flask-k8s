from flask import Blueprint
from flask_cors import *

# 定义蓝图
istio = Blueprint('istio',__name__,url_prefix='/api/k8s/istio')
CORS(istio, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.istio import views