"""
Reads the list of available API versions and prints them. Similar to running
`kubectl api-versions`.
"""
from flask import Flask,jsonify,Response,make_response,Blueprint,request
from kubernetes import client,config
from dateutil import tz, zoneinfo
import json,os
from datetime import datetime,date
import math
from .k8s_decode import DateEncoder
import requests
import time 
import pytz
import ssl
import yaml
from kubernetes.client.rest import ApiException

k8s_op = Blueprint('k8s_op',__name__,url_prefix='/k8s_op')

dir_path = os.path.dirname(os.path.abspath(__file__))

def utc_to_local(utc_time_str, utc_format='%Y-%m-%dT%H:%M:%S.%fZ'):
    local_tz = pytz.timezone('Asia/Shanghai')
    local_format = "%Y-%m-%d %H:%M:%S"
    utc_dt = datetime.strptime(utc_time_str, utc_format)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    time_str = local_dt.strftime(local_format)
    return time_str
    # return datetime.fromtimestamp(int(time.mktime(time.strptime(time_str, local_format))))
    

@k8s_op.route('/create_deploy_by_yaml',methods=('GET','POST'))
def create_deploy_by_yaml():
    if request.method == "POST":
        data = request.get_data()
        print(data)
        json_data = json.loads(data.decode("utf-8"))
        print(json_data)
        yaml_name = json_data.get("yaml_name")
        print(yaml_name)
        if yaml_name == None:
            msg = "需要提供yaml文件" 
            return jsonify({"error":"1001","msg":msg})
        yaml_dir = os.path.join(dir_path,"yaml")
        file_path = os.path.join(yaml_dir,yaml_name)
        print(file_path)
        if not os.path.exists(file_path):
            msg = "找不到此文件{}".format(file_path)
            return jsonify({"error":"1001","msg":msg})
        
        with open(file_path,encoding='utf-8') as f:
            cfg = f.read()
            obj = yaml.safe_load(cfg)  # 用load方法转字典
            try:
                myclient = client.AppsV1Api()
                resp = myclient.create_namespaced_deployment(body=obj, namespace="default")
                # print(resp)
                print("Deployment created. name='%s' " % resp.metadata.name)
            except ApiException as e:
                print(e)
                return make_response(json.dumps({"error":"1001","msg":str(e)},indent=4, cls=DateEncoder),1001)

            return jsonify({"msg":"创建deployment成功"})

@k8s_op.route('/delete_deploy',methods=('GET','POST'))
def delete_deploy():
    if request.method == "POST":
        data = request.get_data()
        # print(data)
        json_data = json.loads(data.decode("utf-8"))
        print(json_data)
        deploy_name = json_data.get("deploy_name")
        print(deploy_name)
        if deploy_name == None:
            msg = "需要提供deploy文件" 
            return jsonify({"error":"1001","msg":msg})

        myclient = client.AppsV1Api()
        resp = myclient.delete_namespaced_deployment(name=deploy_name,namespace="default",\
                body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5))
        print("Deployment delete status={}".format(str(resp.status)))
        
        return jsonify({"msg":"删除deployment成功"})
        
