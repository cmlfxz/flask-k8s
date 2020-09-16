from flask import Blueprint,request,current_app,jsonify,g
from flask_cors import *
# from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app

# from .k8s_decode import MyEncoder
# import json,os,math,requests,time,pytz,ssl,yaml
from flask_k8s.util import *
from kubernetes import client,config
from kubernetes.client.rest import ApiException


# 定义蓝图
k8s = Blueprint('k8s',__name__,url_prefix='/k8s/')
CORS(k8s, supports_credentials=True, resources={r'/*'})

# 导入views
from flask_k8s.k8s import auth
from flask_k8s.k8s import cluster
from flask_k8s.k8s import config
from flask_k8s.k8s import service
from flask_k8s.k8s import daemonSet
from flask_k8s.k8s import deployment
from flask_k8s.k8s import hpa
from flask_k8s.k8s import istio
from flask_k8s.k8s import namespace
from flask_k8s.k8s import node
from flask_k8s.k8s import pod
from flask_k8s.k8s import service
from flask_k8s.k8s import statefulSet
from flask_k8s.k8s import storage
from flask_k8s.k8s import task

@k8s.after_app_request
def after(resp):
    # print("after is called,set cross")
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name,user,user_id,X-B3-TraceId,X-B3-SpanId,X-B3-Sampled'
    return resp

@k8s.before_app_request
def load_header():
    # print('请求方式:{}'.format(request.method))
    if request.method == 'OPTIONS':
        pass
    if request.method == 'POST':
        try:
            # current_app.logger.debug("headers:{}".format(request.headers))
            cluster_name = request.headers.get('cluster_name').strip()
            print("k8s load_header: 集群名字:{}".format(cluster_name))
            if cluster_name == None:
                print("没有设置cluster_name header")
                pass
            else:
                g.cluster_name = cluster_name
                cluster_config = get_cluster_config(cluster_name)
                set_k8s_config(cluster_config)
        except Exception as e:
            print(e)
    # bug 当获取deployment name list 是request get 方式，不要设置k8s config,GET代码纯粹调试
    if request.method == "GET":
        try:
            # current_app.logger.debug("headers:{}".format(request.headers))
            cluster_name = request.headers.get('cluster_name').strip()
            # print("load_header: 集群名字:{}".format(cluster_name))
        except Exception as e:
            print(e)

def set_k8s_config(cluster_config):
    if cluster_config == None:
        print("获取不到集群配置")
    else:
        cluster_config = my_decode(cluster_config)
        # print("集群配置: \n{}".format(cluster_config))
        tmp_filename = "kubeconfig"
        with open(tmp_filename, 'w+', encoding='UTF-8') as file:
            file.write(cluster_config)
        # 这里需要一个文件
        config.load_kube_config(config_file=tmp_filename)
