from flask import Blueprint
from flask_cors import *

# 定义蓝图
workload = Blueprint('workload',__name__,url_prefix='/api/k8s/workload')
CORS(workload, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.workload import deployment
from flask_k8s.workload import pod
from flask_k8s.workload import hpa
from flask_k8s.workload import daemonSet
from flask_k8s.workload import statefulSet