from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from dateutil import tz, zoneinfo
from datetime import datetime,date
from .k8s_decode import MyEncoder
import json,os,math,requests,time,pytz,ssl,yaml
from .util import str_to_int,str_to_float
# from .util import SingletonDBPool
from .util import time_to_string,utc_to_local
from .util import dir_path,my_encode
from .util import handle_input,handle_toleraion_seconds,handle_toleration_item
from .util import get_cluster_config,simple_error_handle
from .util import handle_cpu,handle_memory,handle_disk_space
from kubernetes import client,config
from kubernetes.client.rest import ApiException

k8s_cluster = Blueprint('k8s_cluster',__name__,url_prefix='/api/k8s/cluster')

CORS(k8s_cluster, supports_credentials=True, resources={r'/*'})

@k8s_cluster.after_request
def after(resp):
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name,user,user_id,X-B3-TraceId,X-B3-SpanId,X-B3-Sampled'
    return resp

def format_float(num):
    return  float("%.2f" % num)

# http://192.168.11.51:1900/apis/metrics.k8s.io/v1beta1/nodes
@k8s_cluster.before_app_request
def load_header():
    # print('请求方式:{}'.format(request.method))
    if request.method == 'OPTIONS':
        pass
    if request.method == 'POST':
        try:
            # current_app.logger.debug("headers:{}".format(request.headers))
            cluster_name = request.headers.get('cluster_name').strip()
            print("load_header: 集群名字:{}".format(cluster_name))
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
        cluster_config  = my_decode(cluster_config)
        # print("集群配置: \n{}".format(cluster_config))
        tmp_filename = "kubeconfig"
        with open(tmp_filename,'w+',encoding='UTF-8') as file:
            file.write(cluster_config)
        #这里需要一个文件
        config.load_kube_config(config_file=tmp_filename)

def get_node_performance(name):
    myclient = client.CustomObjectsApi()
    plural = "{}/{}".format("nodes", name)
    # 这个API不稳定
    # bug当有节点没开，获取不到数据，页面会出不来数据，退而求其次，获取不到，置0
    try:
        node = myclient.list_cluster_custom_object(group="metrics.k8s.io", version="v1beta1", plural=plural)
        node_name = node['metadata']['name']
        cpu = handle_cpu(node['usage']['cpu'])
        memory = handle_memory(node['usage']['memory'])
        node_usage = {"node_name": node_name, "cpu": cpu, "memory": memory}
    except ApiException as e:
        if isinstance(e.body, dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            message = e.body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        # current_app.logger.debug(msg)
        node_usage = {"node_name": name, "cpu": 0, "memory": 0}

    return node_usage

def get_pod_num_by_node(name):
    if not name:
        return simple_error_handle("必须要node name参数")
    myclient = client.CoreV1Api()
    field_selector = "spec.nodeName={}".format(name)
    pods = myclient.list_pod_for_all_namespaces(watch=False,field_selector=field_selector)
    return len(pods.items)

@k8s_cluster.route('/get_node_name_list', methods=('GET', 'POST'))
def get_node_name_list():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()

    node_name_list = []
    for node in nodes.items:
        name = node.metadata.name
        node_name_list.append(name)
    return json.dumps(node_name_list, indent=4)

def create_single_node_obj(node):
    meta = node.metadata
    name = meta.name
    create_time = time_to_string(meta.creation_timestamp)
    labels = meta.labels
    role = labels.get('kubernetes.io/role')
    spec = node.spec
    schedulable = True if node.spec.unschedulable == None else False

    status = node.status
    address = status.addresses[0].address
    # 获取单独node的性能数据
    node_usage = get_node_performance(name)
    # 100m 转成 0.1 以核为单位
    node_cpu_usage = format_float(node_usage.get('cpu') / 1000)
    node_memory_usage = node_usage.get('memory')
    node_pod_num = get_pod_num_by_node(name)

    capacity = status.capacity
    cpu_total = str_to_int(capacity['cpu'])
    memory_total = handle_memory(capacity['memory'])
    pod_total = str_to_int(capacity['pods'])
    disk_space = handle_disk_space(capacity['ephemeral-storage'])
    image_num = len(status.images)

    cpu_usage_percent = format_float(node_cpu_usage / cpu_total * 100)
    memory_usage_percent = format_float(node_memory_usage / memory_total * 100)
    pod_usage_percent = format_float(node_pod_num / pod_total * 100)

    mynode = {}
    mynode["name"] = name
    mynode["role"] = role
    mynode["schedulable"] = schedulable

    # CPU总量
    mynode["cpu_total"] = cpu_total
    mynode["cpu_usage"] = node_cpu_usage
    mynode["cpu_usage_percent"] = cpu_usage_percent
    # 内存部分
    mynode["memory_total"] = memory_total
    mynode["memory_usage"] = node_memory_usage
    mynode["memory_usage_percent"] = memory_usage_percent
    # pod部分
    mynode["pod_total"] = pod_total
    mynode["pod_num"] = node_pod_num
    mynode["pod_usage_percent"] = pod_usage_percent
    mynode["storage"] = disk_space

    mynode["create_time"] = create_time
    return mynode

def create_simple_node_obj(node):
    meta = node.metadata
    name = meta.name
    create_time = time_to_string(meta.creation_timestamp)
    labels = meta.labels
    role = labels.get('kubernetes.io/role')
    spec = node.spec
    pod_cidr = spec.pod_cidr
    taints = spec.taints
    schedulable = True if node.spec.unschedulable == None else False
    status = node.status
    node_info = status.node_info
    address = status.addresses[0].address
    mynode = {}
    mynode["name"] = name
    mynode["role"] = role
    mynode["schedulable"] = schedulable
    mynode['node_info'] = node_info
    mynode["taints"] = taints
    mynode["labels"] = labels
    mynode["pod_cidr"] = pod_cidr
    mynode["create_time"] = create_time
    return mynode

#节点列表页面使用
@k8s_cluster.route('/get_node_detail_list',methods=('GET','POST'))
def get_node_detail_list():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    i = 0
    node_list = []
    for node in nodes.items:
        if (i>=0):
            # print(node)
            mynode = create_simple_node_obj(node)
            node_list.append(mynode)
        i = i + 1
    return json.dumps(node_list,indent=4,cls=MyEncoder)

# 集群详情页面使用
@k8s_cluster.route('/get_node_detail_list_v2',methods=('GET','POST'))
def get_node_detail_list_v2():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    node_list = []
    for node in nodes.items:
        mynode = create_single_node_obj(node)
        node_list.append(mynode)
    return json.dumps(node_list,indent=4,cls=MyEncoder)

def get_single_node_capacity(name):
    nodes = client.CoreV1Api().list_node()
    capacity = None
    for node in nodes.items:
        if name == node.metadata.name:
            capacity = node.status.capacity
            break
    return capacity

@k8s_cluster.route('/get_cluster_stats',methods=('GET','POST'))
def get_cluster_stats():
    try:
        data = json.loads(request.get_data().decode("utf-8"))
        stat_type =  handle_input(data.get('stat_type'))
    except:
        data = None
        stat_type = None
    current_app.logger.debug("接收到的数据:{}".format(data))

    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    node_list = []
    cluster_cpu = 0
    cluster_cpu_usage = 0
    cluster_memory = 0
    cluster_memory_usage = 0
    cluster_disk_cap = 0
    cluster_pod_cap = 0
    cluster_pod_usage= 0
    cluster_stat_list = []

    stat_node_list = []
    #先生成node列表
    for node in nodes.items:
        meta = node.metadata
        name = meta.name
        schedulable = True if node.spec.unschedulable == None else False
        if stat_type == 'all':
            stat_node_list.append(name)
        elif stat_type == 'unschedule':
            if schedulable == False:
                stat_node_list.append(name)
        # 默认值统计schedule的数据
        else:
            if schedulable == True:
                stat_node_list.append(name)
    # print(stat_node_list,len(stat_node_list))
    for name in stat_node_list:
        # 获取单独node的性能数据
        # print(name)
        node_usage = get_node_performance(name)
        # 100m 转成 0.12 已核为单位
        node_cpu_usage = format_float(node_usage.get('cpu') / 1000)
        # current_app.logger.debug("node_cpu_usage:{}".format(node_cpu_usage))
        node_memory_usage = node_usage.get('memory')
        node_pod_num = get_pod_num_by_node(name)
        #bug
        capacity = get_single_node_capacity(name)
        # capacity = node.status.capacity
        # 搜集数量
        cpu_total = str_to_int(capacity['cpu'])
        memory_total = handle_memory(capacity['memory'])
        pod_total = str_to_int(capacity['pods'])
        disk_space = handle_disk_space(capacity['ephemeral-storage'])

        # 集群CPU总数
        cluster_cpu = cluster_cpu + cpu_total
        # 集群CPU使用量
        cluster_cpu_usage = cluster_cpu_usage + node_cpu_usage
        # current_app.logger.debug("cluster_cpu_usage:{}".format(cluster_cpu_usage))
        # 集群内存总量
        cluster_memory = cluster_memory + memory_total
        # 集群内存使用量
        cluster_memory_usage = cluster_memory_usage + node_memory_usage
        # 磁盘总量
        cluster_disk_cap = cluster_disk_cap + disk_space
        # 集群pod总量
        cluster_pod_cap = cluster_pod_cap + pod_total
        # 集群pod数量
        cluster_pod_usage = cluster_pod_usage + node_pod_num
    cluster_cpu_usage_percent = format_float(cluster_cpu_usage/cluster_cpu * 100)
    cluster_cpu_usage = format_float(cluster_cpu_usage)
    cluster_cpu_detail = "{}/{} {}%".format(cluster_cpu_usage, cluster_cpu,cluster_cpu_usage_percent)

    cluster_memory_usage_percent = format_float(cluster_memory_usage/cluster_memory * 100)
    cluster_memory_detail = "{}/{} {}%".format(cluster_memory_usage,cluster_memory,cluster_memory_usage_percent)

    cluster_pod_usage_percent = format_float(cluster_pod_usage/cluster_pod_cap * 100)
    cluster_pod_detail = "{}/{} {}%".format(cluster_pod_usage,cluster_pod_cap,cluster_pod_usage_percent)

    cluster_stat = {}
    # cluster_stat["cpu_detail"] = cluster_cpu_detail
    # cluster_stat["memory_detail"] = cluster_memory_detail
    # cluster_stat["pod_detail"] = cluster_pod_detail
    # cluster_stat["disk_cap"] = cluster_disk_cap
    # CPU详情
    cluster_stat["cpu_total"] = cluster_cpu
    cluster_stat["cpu_usage"] = cluster_cpu_usage
    cluster_stat["cpu_usage_percent"] = cluster_cpu_usage_percent
    #内存详情
    cluster_stat["memory_total"] = format_float(cluster_memory/1024)
    cluster_stat["memory_usage"] = format_float(cluster_memory_usage/1024)
    cluster_stat["memory_usage_percent"] = cluster_memory_usage_percent
    #POD详情
    cluster_stat["pod_total"] = cluster_pod_cap
    cluster_stat["pod_usage"] = cluster_pod_usage
    cluster_stat["pod_usage_percent"] = cluster_pod_usage_percent

    cluster_stat["disk"] = cluster_disk_cap

    cluster_stat_list.append(cluster_stat)
    return json.dumps(cluster_stat_list,indent=4,cls=MyEncoder)
    # return json.dumps({"cluster_stat_list":cluster_stat_list})

@k8s_cluster.route('/get_component_status_list',methods=('GET','POST'))
def get_component_status_list():
    myclient = client.CoreV1Api()
    ss = myclient.list_component_status()
    i = 0
    component_status_list = []
    for cs in ss.items:
        if (i>=0):
            conditions = cs.conditions
            meta = cs.metadata
            name = meta.name
            # j = 0
            # for C in conditions:
            #     if(j==0):
            #     j = j + 1
            error = conditions[0].error
            message = conditions[0].message
            status = conditions[0].status
            type = conditions[0].type
            name = meta.name
            my_component_status = {}
            my_component_status["name"] =name
            my_component_status["type"] =type
            my_component_status["status"] =status
            my_component_status["message"] =message
            my_component_status["error"] =error
            component_status_list.append(my_component_status)
        i = i +1
    return json.dumps(component_status_list,indent=4)