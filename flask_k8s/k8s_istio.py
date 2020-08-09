from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from dateutil import tz, zoneinfo
from datetime import datetime,date
from .k8s_decode import MyEncoder,DateEncoder
import json,os,math,requests,time,pytz,yaml
from .util import my_decode,my_encode,str_to_int,str_to_float
from .util import time_to_string,utc_to_local
from .util import dir_path
from .util import handle_input,string_to_int
from .util import simple_error_handle,get_cluster_config
from kubernetes import client,config
from kubernetes.client.rest import ApiException


k8s_istio = Blueprint('k8s_istio',__name__,url_prefix='/api/k8s/istio')

CORS(k8s_istio, supports_credentials=True, resources={r'/*'})

@k8s_istio.after_request
def after(resp):
    # print("after is called,set cross")
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name,user,user_id'
    return resp

@k8s_istio.before_app_request
def load_header():
    if request.method == 'OPTIONS':
        pass
    if request.method == 'POST':
        try:
            cluster_name = request.headers.get('cluster_name').strip()
            # print("load_header: 集群名字:{}".format(cluster_name))
            if cluster_name == None:
                print("没有设置cluster_name header")
                pass
            else:
                g.cluster_name = cluster_name
                cluster_config = get_cluster_config(cluster_name)
                set_k8s_config(cluster_config)
        except Exception as e:
            print(e)

def set_k8s_config(cluster_config):
    if cluster_config == None:
        print("获取不到集群配置")
    else:
        cluster_config  = my_decode(cluster_config)
        # print("集群配置: \n{}".format(cluster_config))
        tmp_filename = "kubeconfig"
        with open(tmp_filename,'w+',encoding='UTF-8') as file:
            file.write(cluster_config)
        #这里需要一个文件
        config.load_kube_config(config_file=tmp_filename)

# http://192.168.11.51:1900/apis/security.istio.io/v1beta1/authorizationpolicies
@k8s_istio.route('/get_istio_policy_list', methods=('GET', 'POST'))
def get_istio_policy_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("收到的数据;{}".format(data))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="security.istio.io", version="v1beta1",
                                                      plural="authorizationpolicies")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace, group="security.istio.io",
                                                         version="v1beta1", plural="authorizationpolicies")
    except ApiException as e:
        if isinstance(e.body, dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            message = e.body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        # current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})
    policys = obj['items']
    policy_list = []
    i = 0
    for policy in policys:
        if (i >= 0):
            print(policy)
            meta = policy['metadata']
            spec = policy['spec']
            print(spec)
            name = meta['name']
            namespace = meta['namespace']
            time_str = meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')
            # if spec != {} or spec != None:

            my_policy={}
            my_policy["name"] = name
            my_policy["namespace"] = namespace
            my_policy["spec"] = spec
            # my_policy["name"] = name
            my_policy["create_time"] = create_time
            policy_list.append(my_policy)
        i = i + 1
    return json.dumps(policy_list, indent=4, cls=MyEncoder)
    # return jsonify({"ok":"get policy list"})

@k8s_istio.route('/delete_istio_policy', methods=('GET', 'POST'))
def delete_istio_policy():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.CustomObjectsApi()
    try:
        api_response = myclient.delete_namespaced_custom_object(group="security.istio.io",
                                                                version="v1beta1",
                                                                plural="authorizationpolicies",
                                                                namespace=namespace,
                                                                name=name,
                                                                body=client.V1DeleteOptions(
                                                                    propagation_policy='Foreground',
                                                                    grace_period_seconds=5))

        # print(api_response)
        result = "{}".format(api_response)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})