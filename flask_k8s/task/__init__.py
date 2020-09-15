from flask import Blueprint
from flask_cors import *

# 定义蓝图
task = Blueprint('task',__name__,url_prefix='/api/k8s/task')
CORS(task, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.task import views