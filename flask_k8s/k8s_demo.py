"""
Reads the list of available API versions and prints them. Similar to running
`kubectl api-versions`.
"""
from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from dateutil import tz, zoneinfo
from datetime import datetime,date
from .k8s_decode import MyEncoder,DateEncoder
import json,os,math,requests,time,pytz,ssl,yaml
from .util import get_db_conn,my_decode,my_encode,str_to_int,str_to_float
from .util import SingletonDBPool
from .util import time_to_string,utc_to_local
from .util import dir_path
from .util import handle_input,handle_toleraion_seconds,string_to_int,handle_toleration_item
from .util import simple_error_handle,get_cluster_config
from flask_cors import *
from .k8s_deployment import get_deployment_by_name
from kubernetes import client,config
from kubernetes.client.rest import ApiException

k8s_demo = Blueprint('k8s_demo',__name__,url_prefix='/k8s_demo')

# CORS(k8s_demo, suppors_credentials=True, resources={r'/*'})


@k8s_demo.before_app_request
def load_header():
    if request.method == 'OPTIONS':
        # print('options请求方式')
        pass
    if request.method == 'POST':
        # print('POST请求方式')
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

# @k8s_demo.after_request
# def after(resp):
#     # print("after is called,set cross")
#     resp = make_response(resp)
#     resp.headers['Access-Control-Allow-Origin'] = '*'
#     resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
#     resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name'
#     return resp

def update_deployment(deploy_name, namespace, image=None, replicas=None, pod_anti_affinity_type=None,
                      anti_affinity_key=None, anti_affinity_value=None):
    # '/apis/apps/v1/namespaces/{namespace}/deployments/{name}', 'PATCH'
    current_app.logger.debug("replicas:{} ".format(replicas))
    deployment = get_deployment_by_name(namespace, deploy_name)
    if (deployment == None):
        return jsonify({"error": "1003", "msg": "找不到该deployment"})
    if image:
        deployment.spec.template.spec.containers[0].image = image
    if replicas:
        deployment.spec.replicas = replicas
    # affinity = None
    # if pod_anti_affinity_type:
    #     if pod_anti_affinity_type == "required":
    #         # anti_affinity_type = "requiredDuringSchedulingIgnoredDuringExecution"
    #         label_selector = client.V1LabelSelector(match_expressions=[
    #             client.V1LabelSelectorRequirement(key=anti_affinity_key, operator='In', values=[anti_affinity_value])
    #         ])
    #         # label_selector = client.V1LabelSelector(match_expressions=[ client.V1LabelSelectorRequirement(key='app',operator=None)])
    #         # # label_selector = None
    #         affinity = client.V1Affinity(
    #             pod_anti_affinity=client.V1PodAntiAffinity(
    #                 required_during_scheduling_ignored_during_execution=[
    #                     # client.re V1PreferredSchedulingTerm
    #                     # client.V1Pod
    #                     client.V1PodAffinityTerm(
    #                         label_selector=label_selector,
    #                         topology_key='kubernetes.io/hostname'
    #                     )
    #                 ]
    #             )
    #         )
    #         print("{}".format(affinity))
    #     else:
    #         pass
    # if affinity:
    #     deployment.spec.template.spec.affinity = affinity
    current_app.logger.debug(deployment)
    try:
        ResponseNotReady = client.AppsV1Api().patch_namespaced_deployment(
            name=deploy_name,
            namespace=namespace,
            body=deployment
        )
    except ApiException as e:
        body = json.loads(e.body)
        msg = {"status": e.status, "reason": e.reason, "message": body['message']}
        return jsonify({'error': '创建失败', "msg": msg})

    return jsonify({"ok": "更新deployment成功"})

@k8s_demo.route('/update_deploy',methods=('GET','POST'))
def update_deploy():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("接受到的数据:{}".format(data))
    namespace = handle_input(data.get('namespace'))
    deploy_name =handle_input(data.get('deploy_name'))
    replicas = str_to_int(handle_input(data.get('replicas')))
    current_app.logger.debug("replicas:{} ".format(replicas))
    project = handle_input(data.get('project'))
    env = handle_input(data.get('env'))
    imageRepo = handle_input(data.get('imageRepo'))
    imageName = handle_input(data.get('imageName'))
    imageTag = handle_input(data.get('imageTag'))
    if (imageRepo!=None and project !=None and env!=None and imageName!=None and imageTag!=None):
        image = "{}/{}-{}/{}:{}".format(imageRepo,project,env,imageName,imageTag)
    else:
        image = None
    pod_anti_affinity_type = handle_input(data.get('pod_anti_affinity_type'))
    anti_affinity_key = handle_input(data.get('anti_affinity_key'))
    anti_affinity_value = handle_input(data.get('anti_affinity_value'))
    print("image值{}".format(image))
    return update_deployment(deploy_name=deploy_name,namespace=namespace,replicas=replicas,image=image,
                             pod_anti_affinity_type=pod_anti_affinity_type,anti_affinity_key=anti_affinity_key,anti_affinity_value=anti_affinity_value)
