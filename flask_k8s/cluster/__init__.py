from flask import Blueprint
from flask_cors import *

# 定义蓝图
cluster = Blueprint('cluster',__name__,url_prefix='/api/k8s/cluster')
CORS(cluster, supports_credentials=True, resources={r'/*'})

#单独导出函数 deployment pod都会用到
from flask_k8s.cluster.views import get_event_list_by_name
# 导入views
from flask_k8s.cluster import views
from flask_k8s.cluster import namespace
from flask_k8s.cluster import node