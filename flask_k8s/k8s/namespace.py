from flask import Flask,jsonify,Blueprint,request,current_app
from flask_cors import *
from flask_k8s.k8s_decode import MyEncoder
from flask_k8s.util import *
from .cluster import get_event_list_by_name

from kubernetes import client,config
from kubernetes.client.rest import ApiException


# 导入蓝图
from flask_k8s.k8s import k8s

#列出namespace
@k8s.route('/get_namespace_list',methods=('GET','POST'))
def get_namespace_list():
    myclient = client.CoreV1Api()
    namespace_list = []
    for ns in myclient.list_namespace().items:
        meta = ns.metadata
        create_time = time_to_string(meta.creation_timestamp)
        status = ns.status.phase
        namespace= {"name":meta.name,"status":status,"labels":meta.labels,"create_time":create_time}
        namespace_list.append(namespace)
    return json.dumps(namespace_list,indent=4)

@k8s.route('/get_namespace_name_list',methods=('GET','POST'))
def get_namespace_name_list():
    myclient = client.CoreV1Api()
    namespace_name_list = []
    for item in myclient.list_namespace().items:
        name = item.metadata.name
        namespace_name_list.append(name)
    return json.dumps(namespace_name_list,indent=4)

def create_namespace_resource(name,labels=None):
        myclient = client.CoreV1Api()
        if labels:
            metadata = client.V1ObjectMeta(name=name,labels=labels)
        else:
            metadata = client.V1ObjectMeta(name=name)
        namespace = client.V1Namespace(
            api_version="v1",
            kind="Namespace",
            metadata=metadata
        )
        try:
            result = myclient.create_namespace(body=namespace)
            # print(type(result),result)
        except ApiException as e:
            # print("status:{}".format(e.status))
            # print("reason:{}".format(e.reason))
            # print("body:{}".format(e.body))
            # body = json.loads(e.body)
            # print(type(e.body))
            # print("message:{},{},{}".format(body['message'],body['code'],body['status']))
            # print("headers:{}".format(e.headers))
            body = json.loads(e.body)
            msg={"status":e.status,"reason":e.reason,"message":body['message']}
            return jsonify({'error': '创建失败',"msg":msg})
            
        return jsonify({'ok': '创建成功'})

@k8s.route('/create_namespace', methods=('GET', 'POST'))
def create_namespace():
    data = json.loads(request.get_data().decode('utf-8'))
    # {"project_name": "ms", "env_name": "dev", "cluster_name": "k8s_c1", "istio_inject": "on"}
    print("接收到的数据:{}".format(data))
    project_name = handle_input(data.get('project_name'))
    env_name = handle_input(data.get('env_name'))
    name = "{}-{}".format(project_name,env_name)
    # print(name)
    labels = {}
    istio_inject = handle_input(data.get('istio_inject'))
    # print("istio_inject:{}".format(istio_inject))
    if istio_inject:
        labels['istio-injection'] = "enabled"
    else:
        labels = None
    # print("labels:{}".format(labels))
    return create_namespace_resource(name=name,labels=labels)

def get_namespace_by_name(name):
    # namespaces = client.AppsV1Api().list_namespaced_namespace(namespace=namespace)
    namespaces = client.CoreV1Api().list_namespace()
    namespace = None
    for ns in namespaces.items:
        if ns.metadata.name == name:
            namespace = ns
            break
    return namespace

@k8s.route('/update_namespace', methods=('GET', 'POST'))
def update_namespace():
    # {"name": name, "labels": labels, "action": "remove_istio_inject"}
    data = json.loads(request.get_data().decode('utf-8'))
    print("update_namespace接收到的数据：{}".format(data))
    name = handle_input(data.get('name'))
    namespace = get_namespace_by_name(name)
    if not namespace:
        return jsonify({"error":"找不到此名称空间"})
    # flask-admin收到的是字典
    labels = data.get('labels')
    print(type(labels),isinstance(labels,str))
    if labels == None:
        labels = {}
    elif(isinstance(labels,str)):
        labels = json.loads(labels)
    else:
        pass
    action = handle_input(data.get('action'))
    if action=="remove_istio_inject":
        labels.pop('istio-injection')
        # print("移除isito标签后: {}".format(labels))
    elif action == "add_istio_inject":
        labels['istio-injection'] = "enabled"
    else:
        return jsonify({"error":"暂时还没有实现此操作"})
    # namespace.metadata.cluster_name="k8s_cs1"
    namespace.metadata.labels = labels
    myclient = client.CoreV1Api()
    # print("命名空间:{}\n".format(namespace))
    try:
        result = myclient.replace_namespace(name,body=namespace)
    except Exception as e:
        print(e)
        return jsonify({"error":"更新命名空间出现异常"})
    return jsonify({"ok":"更新命名空间成功"})

@k8s.route('/delete_namespace', methods=('GET', 'POST'))
def delete_namespace():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    myclient = client.CoreV1Api()
    try:
        result = myclient.delete_namespace(name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除命名空间出现异常',"msg":msg})
    return jsonify({"ok":"删除成功"})
