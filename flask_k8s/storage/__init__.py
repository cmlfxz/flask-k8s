

from flask import Blueprint
from flask_cors import *

# 定义蓝图
storage = Blueprint('storage',__name__,url_prefix='/api/k8s/storage')
CORS(storage, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.storage import views