from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from dateutil import tz, zoneinfo
from datetime import datetime,date
from .k8s_decode import MyEncoder,DateEncoder
import json,os,math,requests,time,pytz,yaml
from .util import get_db_conn,my_decode,my_encode,str_to_int,str_to_float
from .util import time_to_string,utc_to_local
from .util import dir_path
from .util import handle_input
from .util import simple_error_handle,get_cluster_config

from kubernetes import client,config
from kubernetes.client.rest import ApiException
from kubernetes.client.models.v1_namespace import V1Namespace

k8s_auth = Blueprint('k8s_auth',__name__,url_prefix='/api/k8s/auth')

CORS(k8s_auth, supports_credentials=True, resources={r'/*'})

# @k8s_auth.after_request
# def after(resp):
#     # print("after is called,set cross")
#     resp = make_response(resp)
#     resp.headers['Access-Control-Allow-Origin'] = '*'
#     resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
#     resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name,user,user_id'
#     return resp
#
# @k8s_auth.before_request
# def load_header():
#     if request.method == 'OPTIONS':
#         pass
#     if request.method == 'POST':
#         try:
#             # current_app.logger.debug("headers:{}".format(request.headers))
#             cluster_name = request.headers.get('cluster_name').strip()
#             print("auth load_header: 集群名字:{}".format(cluster_name))
#             if cluster_name == None:
#                 print("没有设置cluster_name header")
#                 pass
#             else:
#                 g.cluster_name = cluster_name
#                 cluster_config = get_cluster_config(cluster_name)
#                 set_k8s_config(cluster_config)
#         except Exception as e:
#             print(e)
#     if request.method == "GET":
#         try:
#             current_app.logger.debug("headers:{}".format(request.headers))
#             # cluster_name = request.headers.get('cluster_name').strip()
#             # print("load_header: 集群名字:{}".format(cluster_name))
#         except Exception as e:
#             print(e)
#
# def set_k8s_config(cluster_config):
#     if cluster_config == None:
#         print("获取不到集群配置")
#     else:
#         cluster_config  = my_decode(cluster_config)
#         # print("集群配置: \n{}".format(cluster_config))
#         tmp_filename = "kubeconfig"
#         with open(tmp_filename,'w+',encoding='UTF-8') as file:
#             file.write(cluster_config)
#         #这里需要一个文件
#         config.load_kube_config(config_file=tmp_filename)

@k8s_auth.route('get_service_account_list',methods=('GET','POST'))
def get_service_account_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("sa接收的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all":
        sas = myclient.list_service_account_for_all_namespaces()
    else:
        sas =myclient.list_namespaced_service_account(namespace=namespace)
    i = 0
    sa_list = []
    for sa in sas.items:
        if (i >= 0):
            # print(sa)
            meta = sa.metadata
            create_time = time_to_string(meta.creation_timestamp)
            name = meta.name
            namespace = meta.namespace
            labels = meta.labels
            image_pull_secrets = sa.image_pull_secrets
            secrets  = sa.secrets
            secret_list = []
            for secret in secrets:
                secret_name = secret.name
                my_secret = {}
                my_secret['name'] = secret_name
                secret_list.append(my_secret)
            my_sa = {}
            my_sa["name"] = name
            my_sa["namespace"] =namespace
            my_sa["labels"] = labels
            my_sa["secret_list"] = secret_list
            my_sa["create_time"] =create_time
            sa_list.append(my_sa)
            # print(sa_list)

        i= i+1
    return json.dumps(sa_list,indent=4,cls=MyEncoder)
    # return jsonify({"ok":"get sa list"})

@k8s_auth.route('/delete_service_account', methods=('GET', 'POST'))
def delete_service_account():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.CoreV1Api()
    try:
        result = myclient.delete_namespaced_service_account(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_auth.route('get_cluster_role_list',methods=('GET','POST'))
def get_cluster_role_list():
    myclient = client.RbacAuthorizationV1Api()
    cluster_roles = myclient.list_cluster_role()
    i = 0
    cluster_role_list = []
    for cluster_role in cluster_roles.items:
        if (i >= 0):
            # print(cluster_role)
            meta = cluster_role.metadata
            create_time = time_to_string(meta.creation_timestamp)
            name = meta.name
            labels = meta.labels

            rules  = cluster_role.rules
            rule_list = []
            if rules != None:
                for rule in rules:
                    # print(rule)
                    my_rule = {}
                    my_rule['api_groups'] = rule.api_groups
                    my_rule['resources'] = rule.resources
                    my_rule['verbs'] = rule.verbs
                    rule_list.append(my_rule)
            my_cluster_role = {}
            my_cluster_role["name"] = name
            # my_cluster_role["labels"] = labels
            my_cluster_role["rule_list"] = rule_list
            my_cluster_role["create_time"] =create_time
            cluster_role_list.append(my_cluster_role)
            # print(cluster_role_list)

        i= i+1
    return json.dumps(cluster_role_list,indent=4,cls=MyEncoder)
    # return jsonify({"ok":"get sa list"})
@k8s_auth.route('/delete_cluster_role', methods=('GET', 'POST'))
def delete_cluster_role():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    myclient = client.RbacAuthorizationV1Api()
    try:
        result = myclient.delete_cluster_role(name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_auth.route('get_cluster_role_binding_list',methods=('GET','POST'))
def get_cluster_role_binding_list():
    myclient = client.RbacAuthorizationV1Api()
    crbs = myclient.list_cluster_role_binding()
    i = 0
    crb_list = []
    for crb in crbs.items:
        if (i >= 0):
            # print(crb)
            meta = crb.metadata
            create_time = time_to_string(meta.creation_timestamp)
            name = meta.name
            labels = meta.labels

            role_ref = crb.role_ref
            # my_role_ref = {}
            # # my_role_ref["api_group"] = role_ref.api_group
            # my_role_ref["kind"] = role_ref.kind
            # my_role_ref["name"] = role_ref.name
            my_role_ref = "{}/{}".format(role_ref.kind,role_ref.name)

            subjects = crb.subjects
            subject_list = []
            if subjects != None:
                for subject in subjects:
                    # my_subject = {}
                    # my_subject['kind'] = subject.kind
                    # my_subject['name'] = subject.name
                    # my_subject['namespace'] = subject.namespace
                    my_subject = "{}/{}/{}".format(subject.namespace,subject.kind,subject.name)
                    subject_list.append(my_subject)

            my_crb = {}
            my_crb["name"] = name
            # my_crb["labels"] = labels
            my_crb["role_ref(角色)"] = my_role_ref
            my_crb["account(账号)"] = my_subject
            my_crb["create_time"] =create_time
            crb_list.append(my_crb)
            # print(crb_list)

        i= i+1
    return json.dumps(crb_list,indent=4,cls=MyEncoder)
    # return jsonify({"ok":"get sa list"})

@k8s_auth.route('/delete_cluster_role_binding', methods=('GET', 'POST'))
def delete_cluster_role_binding():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    myclient = client.RbacAuthorizationV1Api()
    try:
        result = myclient.delete_cluster_role_binding(name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_auth.route('get_role_list',methods=('GET','POST'))
def get_role_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接受的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.RbacAuthorizationV1Api()
    if namespace == "" or namespace == "all":
        roles = myclient.list_role_for_all_namespaces(watch=False)
    else:
        roles = myclient.list_namespaced_role(namespace=namespace)
    i = 0
    role_list = []
    for role in roles.items:
        if (i >= 0):
            # print(role)
            meta = role.metadata
            create_time = time_to_string(meta.creation_timestamp)
            name = meta.name
            namespace = meta.namespace
            # labels = meta.labels

            rules  = role.rules
            rule_list = []
            for rule in rules:
                my_rule = {}
                my_rule['api_groups'] = rule.api_groups
                my_rule['resources'] = rule.resources
                my_rule['verbs'] = rule.verbs
                rule_list.append(my_rule)
            my_role = {}
            my_role["name"] = name
            my_role["namespace"] =namespace
            # my_role["labels"] = labels
            my_role["rule_list"] = rule_list
            my_role["create_time"] =create_time
            role_list.append(my_role)
            # print(role_list)

        i= i+1
    return json.dumps(role_list,indent=4,cls=MyEncoder)
    # return jsonify({"ok":"get sa list"})

@k8s_auth.route('/delete_role', methods=('GET', 'POST'))
def delete_role():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")

    myclient = client.RbacAuthorizationV1Api()
    try:
        result = myclient.delete_namespaced_role(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_auth.route('get_role_binding_list',methods=('GET','POST'))
def get_role_binding_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接受的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.RbacAuthorizationV1Api()
    if namespace == "" or namespace == "all":
        rbs = myclient.list_role_binding_for_all_namespaces(watch=False)
    else:
        rbs = myclient.list_namespaced_role_binding(namespace=namespace)
    i = 0
    rb_list = []
    for rb in rbs.items:
        if (i >= 0):
            # print(rb)
            meta = rb.metadata
            create_time = time_to_string(meta.creation_timestamp)
            name = meta.name
            namespace = meta.namespace
            labels = meta.labels

            role_ref = rb.role_ref
            # my_role_ref = {}
            # # my_role_ref["api_group"] = role_ref.api_group
            # my_role_ref["kind"] = role_ref.kind
            # my_role_ref["name"] = role_ref.name
            my_role_ref = "{}/{}".format(role_ref.kind,role_ref.name)

            subjects = rb.subjects
            subject_list = []
            if subjects != None:
                for subject in subjects:
                    # my_subject = {}
                    # my_subject['kind'] = subject.kind
                    # my_subject['name'] = subject.name
                    # my_subject['namespace'] = subject.namespace
                    my_subject = "{}/{}/{}".format(subject.namespace,subject.kind,subject.name)
                    subject_list.append(my_subject)

            my_rb = {}
            my_rb["name"] = name
            my_rb["namespace"] =namespace
            # my_rb["labels"] = labels
            my_rb["role_ref"] = my_role_ref
            my_rb["subjects"] = my_subject
            my_rb["create_time"] =create_time
            rb_list.append(my_rb)
            # print(rb_list)

        i= i+1
    return json.dumps(rb_list,indent=4,cls=MyEncoder)
    # return jsonify({"ok":"get sa list"})

@k8s_auth.route('/delete_role_binding', methods=('GET', 'POST'))
def delete_role_binding():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")

    myclient = client.RbacAuthorizationV1Api()
    try:
        result = myclient.delete_namespaced_role_binding(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})


