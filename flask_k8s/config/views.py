from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from dateutil import tz, zoneinfo
from datetime import datetime,date
from flask_k8s.k8s_decode import MyEncoder
import json,os,math,requests,time,pytz,ssl,yaml
from flask_k8s.util import *
from kubernetes import client,config
from kubernetes.client.rest import ApiException


# 导入蓝图
from flask_k8s.config import config



@config.route('/get_configmap_list',methods=('GET','POST'))
def get_configmap_list():  
    # myclient = client.AppsV1Api()
    # configmaps = myclient.list_namespaced_config_map(namespace="ms-prod")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = handle_input(data.get("namespace"))
    print("get_configmap_list收到的数据:{}".format(data))
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all": 
        configmaps = myclient.list_config_map_for_all_namespaces()
    else:
        configmaps = myclient.list_namespaced_config_map(namespace=namespace)
        
    configmap_list = []
    i = 0 
    for configmap in configmaps.items:
        if (i >=0):
            # print(configmap)
            meta = configmap.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
            data = configmap.data    
            
            myconfigmap = {"name":name,"namespace":namespace,"labels":labels,"create_time":create_time}    
            configmap_list.append(myconfigmap) 
        i = i +1
    return json.dumps(configmap_list,indent=4,cls=MyEncoder)
    # return jsonify({'a':1})
    

@config.route('/get_cm_detail',methods=('GET','POST'))        
def get_cm_detail():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("收到的数据:{}".format(data))
    namespace =  handle_input(data.get("namespace"))
    cm_name = handle_input(data.get('name'))
    myclient = client.CoreV1Api()
    field_selector="metadata.name={}".format(cm_name)
    # current_app.logger.debug(field_selector)
    configmaps = myclient.list_namespaced_config_map(namespace=namespace,field_selector=field_selector)
    configmap = None
    for item in configmaps.items:
        if item.metadata.name == cm_name:
            configmap = item
            break
    if configmap == None:
        return simple_error_handle("找不到configmap相关信息")

    meta = configmap.metadata
    name = meta.name
    create_time = time_to_string(meta.creation_timestamp)

    labels = meta.labels
    namespace = meta.namespace
    data = configmap.data
    # print(type(data),data)
    # for k,v in data.items():
    #     print(k,v)
    mycm = {
        "name":name,
        "namespace":namespace,
        "labels":labels,
        "create_time":create_time,
        "data":data
    }          
    return json.dumps(mycm,indent=4,cls=MyEncoder)

#列出namespace
@config.route('/get_secret_list',methods=('GET','POST'))
def get_secret_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all": 
        secrets = myclient.list_secret_for_all_namespaces(watch=False)
    else:
        secrets = myclient.list_namespaced_secret(namespace=namespace)
    # myclient = client.CoreV1Api()
    # secrets = myclient.list_namespaced_secret("ms-prod")
    secret_list = []
    i = 0 
    for secret in secrets.items:
        if (i >=0):
            # print(secret)
            meta = secret.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
            data = secret.data
            type = secret.type
            
            mysecret = {"name":name,"namespace":namespace,"type":type,"create_time":create_time}
            secret_list.append(mysecret) 
        i = i +1
    return json.dumps(secret_list,indent=4,cls=MyEncoder)

@config.route('/get_secret_detail',methods=('GET','POST'))        
def get_secret_detail():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("收到的数据:{}".format(data))
    namespace =  handle_input(data.get("namespace"))
    secret_name = handle_input(data.get('name'))
    myclient = client.CoreV1Api()
    field_selector="metadata.name={}".format(secret_name)
    current_app.logger.debug(field_selector)
    secrets = myclient.list_namespaced_secret(namespace=namespace,field_selector=field_selector)
    secret = None
    for item in secrets.items:
        if item.metadata.name == secret_name:
            secret = item
            break
    if secret == None:
        return simple_error_handle("找不到secret相关信息")
    meta = secret.metadata
    name = meta.name
    create_time = time_to_string(meta.creation_timestamp)
    labels = meta.labels
    namespace = meta.namespace
    data = secret.data
    secret_type = secret.type
    # current_app.logger.debug(type(data),data)
    data_list = []
    if data != None:
        for k,v in data.items():
            value = ""
            try:
                value = my_decode(v)
            except Exception as e:
                print("secret base64解密失败")
                value = v
            item = {
                "key":k,
                "value":value,
            }
            data_list.append(item)

    #     data返回列表吧
    mysecret = {
        "name":name,
        "namespace":namespace,
        "labels":labels,
        "create_time":create_time,
        "type":secret_type,
        "data":data_list,
    }          
    return json.dumps(mysecret,indent=4,cls=MyEncoder)


@config.route('/delete_configmap',methods=('GET','POST'))
def delete_configmap():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))
    
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.CoreV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_config_map(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除configmap异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@config.route('/delete_secret', methods=('GET', 'POST'))
def delete_secret():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))

    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.CoreV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_secret(namespace=namespace, name=name)
        # result = myclient.delete_namespaced_config_map(namespace=namespace, name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg = {"status": e.status, "reason": e.reason, "message": body['message']}
        return jsonify({'error': '删除secret异常', "msg": msg})
    return jsonify({"ok": "删除成功"})