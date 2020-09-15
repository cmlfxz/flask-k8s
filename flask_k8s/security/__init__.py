from flask import Blueprint
from flask_cors import *

# 定义蓝图
security = Blueprint('security',__name__,url_prefix='/api/k8s/security')
CORS(security, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.security import views