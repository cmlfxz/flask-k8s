"""
Reads the list of available API versions and prints them. Similar to running
`kubectl api-versions`.
"""
from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from kubernetes import client,config
from dateutil import tz, zoneinfo
import json,os
from datetime import datetime,date
import math
from .k8s_decode import MyEncoder
import requests
import time
import ssl
from .util import get_db_conn,my_decode,my_encode,str_to_int,str_to_float
from .util import SingletonDBPool
from .util import time_to_string,utc_to_local
from .util import dir_path
from .util import handle_input,handle_toleraion_seconds,string_to_int,handle_toleration_item
from flask_cors import *
import pprint

k8s = Blueprint('k8s',__name__,url_prefix='/k8s')

CORS(k8s, suppors_credentials=True, resources={r'/*'})

def takename(e):
    return e['name']


# http://192.168.11.51:1900/apis/metrics.k8s.io/v1beta1/nodes 

@k8s.before_app_request
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

@k8s.after_request
def after(resp):
    # print("after is called,set cross")
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name'
    return resp

def handle_cpu(cpu):
    if cpu == "0":
        return 0
    elif cpu.endswith('n'):
        # 返回m为单位的cpu值
        # return int(cpu.split('n')[0])/1000/1000
        return math.ceil(int(cpu.split('n')[0])/1000/1000)
    else:
        print("出现未识别的CPU格式{}".format(cpu))
        return 0

def handle_disk_space(disk):
    if disk == "0":
        return 0
    elif disk.endswith('Ki'):
        # 转成G单位大小
        return math.ceil(int(disk.split('Ki')[0])/1024/1024)
    elif disk.endswith('Mi'):
        return math.ceil(int(disk.split('Mi')[0])/1024)
    else:
        print("出现未识别的disk_space格式{}".format(disk))
        return 0

def handle_memory(memory):
    if memory == "0":
        return 0
    elif memory.endswith('Ki'):
        return math.ceil(int(memory.split('Ki')[0])/1024)
    elif memory.endswith('Mi'):
        return math.ceil(int(memory.split('Mi')[0]))
    else:
        print("出现未识别的内存格式{}".format(memory))
        return 0
    
def get_named_node_usage_detail(name):
    myclient = client.CustomObjectsApi()
    plural = "{}/{}".format("nodes",name)
    current_app.logger.debug(plural)
    # 这个API不稳定
    node = myclient.list_cluster_custom_object(group="metrics.k8s.io",version="v1beta1",plural=plural)
    node_name = node['metadata']['name']

    cpu = handle_cpu(node['usage']['cpu'])
    node_cpu_usage = "{}m".format(math.ceil(cpu))
    memory = handle_memory(node['usage']['memory'])
    node_memory_usage = "{}Mi".format(float('%.2f' % memory))
    node_usage = {"node_name":node_name,"cpu":cpu,"memory":memory}
    return node_usage
    
def get_node_usage_detail(): 
    myclient = client.CustomObjectsApi()
    nodes = myclient.list_cluster_custom_object(group="metrics.k8s.io",version="v1beta1",plural="nodes")
    
    i = 0
    node_usage_list = []
    for node in nodes['items']:
        if i >= 0:
            # print(node)
            node_name = node['metadata']['name']
            cpu = handle_cpu(node['usage']['cpu'])
            node_cpu_usage = "{}m".format(math.ceil(cpu))
            memory = handle_memory(node['usage']['memory'])
            node_memory_usage = "{}Mi".format(float('%.2f' % memory))
            node_usage = {"node_name":node_name,"node_cpu_usage":node_cpu_usage,"node_memory_usage":node_memory_usage}
            node_usage_list.append(node_usage)
        i = i +1
    return node_usage_list
        
def get_cluster_config(cluster_name):
    cluster_config = None
    # conn = get_db_conn()
    pool = SingletonDBPool()
    conn = pool.connect()
    if conn == None:
        print("无法获取数据库连接")
    else:
        cursor = conn.cursor()
        sql = "select cluster_config from cluster where cluster_name = \'{}\' ".format(cluster_name)
        try:
            cursor.execute(sql)
            results  =  cursor.fetchone()
            cluster_config = results[0]
        except Exception as e:
            print("查询不到数据")
    conn.close()
    return cluster_config

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

# @k8s.route('/get_node_usage', methods=('GET','POST'))
# def get_node_usage():
#     node_usage_list = get_node_usage_detail()
#     return json.dumps(node_usage_list,indent=4)

@k8s.route('/<version>/get_node_usage', methods=('GET','POST'))
def get_node_usage(version):
    # node_usage_list = get_node_usage_detail()
    if version == "v2":
        print("进入v2版本")
        node_usage_list = get_named_node_usage_detail("192.168.11.51")
    else:
        print("进入v1版本")
        node_usage_list = get_node_usage_detail()
        
    return json.dumps(node_usage_list,indent=4)

def get_pod_usage_detail(namespace=None):
    myclient = client.CustomObjectsApi()
    if namespace == "" or namespace=='all':    
        pods = myclient.list_cluster_custom_object(group="metrics.k8s.io",version="v1beta1",plural="pods")
    else:
        pods = myclient.list_namespaced_custom_object(namespace=namespace,group="metrics.k8s.io", version="v1beta1", plural="pods")
    i = 0
    pod_usage_list = []
    for pod in pods['items']:
        if i >= 0:
            # print(pod)
            namespace = pod['metadata']['namespace']
            pod_name = pod['metadata']['name']

            containers =  pod['containers']
            container_list = []
            j = 0
            cpu_all = 0
            memory_all = 0

            for container in containers:
                container_name = container['name']
                cpu = handle_cpu(container['usage']['cpu'] )
                container_cpu_usage = "{}m".format(math.ceil(cpu))
                memory = handle_memory(container['usage']['memory'])
                container_memory_usage = "{}Mi".format(float('%.2f' % memory))
                container_usage = {"name":container_name,"cpu":container_cpu_usage,"memory":container_memory_usage}
                container_list.append(container_usage)

                #汇总容器数据
                cpu_all = cpu_all + cpu
                memory_all = memory_all + memory
                cpu_all_usage =  "{}m".format(math.ceil(cpu_all))
                memory_all_usage = "{}Mi".format(float('%.2f' % memory_all))

                j = j + 1

            pod_usage = {"pod_name":pod_name,"namespace":namespace,"cpu_all_usage":cpu_all_usage,"memory_all_usage":memory_all_usage,"container_list":container_list}
            pod_usage_list.append(pod_usage)
        i = i +1
    return pod_usage_list

@k8s.route('/get_pod_usage', methods=('GET','POST'))
def get_pod_usage():
    namespace = None
    try:
        data = json.loads(request.get_data().decode('UTF-8'))
        namespace = data.get('namespace').strip()
    except Exception as e:
        print("没有收到namespace:{}".format(e))
    pod_usage_list = get_pod_usage_detail(namespace=namespace)
    return json.dumps(pod_usage_list,indent=4)

#列出gateway
@k8s.route('/get_gateway_list',methods=('GET','POST'))
def get_gateway_list():
    # myclient = client.CustomObjectsApi()
    # obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="gateways")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    if namespace == "" or namespace == "all": 
        obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="gateways")
    else:
        obj = myclient.list_namespaced_custom_object(namespace=namespace,group="networking.istio.io",version="v1alpha3",plural="gateways")  
    gateways = obj['items']
    gateway_list = []
    i = 0
    for gateway in gateways:
        if(i>=0):
            meta = gateway['metadata'] 
            spec = gateway['spec']
            name = meta['name']
            namespace = meta['namespace']
            time_str= meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')
            # Unixtime = time.mktime(time.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ'))
            # create_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(Unixtime))
            selector = spec['selector']
            servers = spec['servers']
            domain_list = []
            for server in servers:
                domain = server['hosts']
                domain_list.append(domain)
            
            mygateway = {"name":name,"namespace":namespace,"selector":selector,"servers":servers,"domain_list":domain_list,"create_time":create_time,}
            gateway_list.append(mygateway)
        i = i + 1
    return json.dumps(gateway_list,indent=4,cls=MyEncoder)

#列出vs
@k8s.route('/get_virtual_service_list',methods=('GET','POST'))
def get_virtual_service_list():
    # myclient = client.CustomObjectsApi()
    # obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="virtualservices")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    if namespace == "" or namespace == "all": 
        obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="virtualservices")
    else:
        obj = myclient.list_namespaced_custom_object(namespace=namespace,group="networking.istio.io",version="v1alpha3",plural="virtualservices")

    virtual_services = obj['items']
    virtual_service_list = []
    i = 0
    for virtual_service in virtual_services:
        if(i>=0):
            meta = virtual_service['metadata'] 
            spec = virtual_service['spec']
            name = meta['name']
            namespace = meta['namespace']
            time_str= meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')
            try:
                gateways = spec['gateways']
            except Exception as e: 
                gateways = None
                # print(e)
            hosts = spec['hosts']
            http = spec['http']
            myvirtual_service = {"name":name,"namespace":namespace,"gateways":gateways,"hosts":hosts,"http":http,"create_time":create_time,}
            virtual_service_list.append(myvirtual_service)
            
        i = i + 1
    return json.dumps(virtual_service_list, indent=4)
    # return json.dumps(virtual_service_list,indent=4,cls=MyEncoder)

#列出vs
@k8s.route('/get_destination_rule_list',methods=('GET','POST'))
def get_destination_rule_list():
    # myclient = client.CustomObjectsApi()
    # obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="destinationrules")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    if namespace == "" or namespace == "all": 
        obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="destinationrules")
    else:
        obj = myclient.list_namespaced_custom_object(namespace=namespace,group="networking.istio.io",version="v1alpha3",plural="destinationrules")
    #obj是一个字典
    destination_rules = obj['items']
    destination_rule_list = []
    i = 0
    for destination_rule in destination_rules:
        if(i>=0):
            # print(destination_rule)
            meta = destination_rule['metadata'] 
            spec = destination_rule['spec']
            name = meta['name']
            namespace = meta['namespace']
            time_str= meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')

            host = spec['host']
            subsets = spec['subsets']
            mydestination_rule = {"name":name,"namespace":namespace,"host":host,"subsets":subsets,"create_time":create_time,}
            destination_rule_list.append(mydestination_rule)
            
        i = i + 1
    return json.dumps(destination_rule_list,indent=4,cls=MyEncoder)

@k8s.route('/get_api_version',methods=['GET','POST'])
def get_api_version():
    list_dict = []
    for api in client.ApisApi().get_api_versions().groups:
        versions = []
        for v in api.versions:
            name  = ""
            if v.version == api.preferred_version.version and len(api.versions) > 1:
                name += "*"
            name += v.version
            versions.append(name)
            #存到字典里面去  
        dict1 = {'name': api.name,'versions':",".join(versions)}
        list_dict.append(dict1)
    list_dict.sort(key=takename)
    return jsonify(list_dict)

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
    # return jsonify(namespace_list)
    return json.dumps(namespace_list,indent=4)
    # return json.dumps(namespace_list,default=lambda obj: obj.__dict__,sort_keys=True,indent=4)

@k8s.route('/get_namespace_name_list',methods=('GET','POST'))
def get_namespace_name_list():
    myclient = client.CoreV1Api()
    namespace_name_list = []
    for item in myclient.list_namespace().items:
        name = item.metadata.name
        namespace_name_list.append(name)
    return json.dumps(namespace_name_list,indent=4)

@k8s.route('/get_service_list',methods=('GET','POST'))
def get_service_list():
    # get_data = request.get_data()
    # print(type(get_data))
    # print("{}".format(get_data))
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    # print(namespace)
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all": 
        services = myclient.list_service_for_all_namespaces(watch=False)
    else:
        #/api/v1/namespaces/{namespace}/services
        services = myclient.list_namespaced_service(namespace=namespace)
    service_list = []
    for service in services.items:
        # print(service)
        meta = service.metadata
        create_time = time_to_string(meta.creation_timestamp)
        name = meta.name 
        cluster_name = meta.cluster_name 
        namespace = meta.namespace
        annotations = meta.annotations
        labels = meta.labels
        spec = service.spec
        cluster_ip = spec.cluster_ip
        policy = spec.external_traffic_policy
        health_check_node_port = spec.health_check_node_port
        load_balancer_ip = spec.load_balancer_ip
        ports = spec.ports
        selector = spec.selector
        service_type = spec.type
        status = service.status
        
        internal_endpoints = []
        
        for p in ports:
            endpoint = "{}.{}:{} {}".format(name,namespace,p.port,p.protocol)
            internal_endpoints.append(endpoint)
            if p.node_port:
                endpoint2 = "{}.{}:{} {}".format(name,namespace,p.node_port,p.protocol)
                internal_endpoints.append(endpoint2)
        service = {"name":name,"namespace":namespace,"service_type":service_type,"ports":ports,\
            "internal_endpoints":internal_endpoints,"labels":labels,"cluster_ip":cluster_ip,\
            "selector":selector,"create_time":create_time}
        service_list.append(service)
    
    # return json.dumps(service_list,default=lambda obj: obj.__dict__,sort_keys=True,indent=4)
    return json.dumps(service_list,indent=4,cls=MyEncoder)

# from flask_k8s.util import *
@k8s.route('/get_pod_list',methods=('GET','POST'))
def get_pod_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all": 
        pods = myclient.list_pod_for_all_namespaces(watch=False)
    else:
        pods = myclient.list_namespaced_pod(namespace=namespace)
    i = 0
    pod_list = []
    for pod in pods.items:
        if (i >=0):
            # print(pod)
            meta = pod.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name

            labels = meta.labels
            namespace = meta.namespace 
            
            spec = pod.spec
            affinity = spec.affinity
            host_network = spec.host_network
            image_pull_secrets = spec.image_pull_secrets
            node_selector = spec.node_selector
            restart_policy = spec.restart_policy
            security_context = spec.security_context
            service_account_name = spec.service_account_name
            tolerations = spec.tolerations

            
            containers = spec.containers
            
            container_name = image = image_pull_policy = ""
            container_info=""
            args = command = ""
            env = ""
            liveness_probe = readiness_probe = ""
            resources = ""
            volume_mounts = ""
            ports = ""
            i = 0
            for c in containers: 
                if (i==0):
                    container_name = c.name
                    args = c.args 
                    command = c.command 
                    env = c.env 
                    image = c.image
                    image_pull_policy  = c.image_pull_policy
                    liveness_probe = c.liveness_probe
                    readiness_probe = c.readiness_probe
                    resources = c.resources
                    volume_mounts = c.volume_mounts
                    ports = c.ports
                    container_info = {"container_name":container_name,"image":image,"image_pull_policy":image_pull_policy,"ports":ports}

                i = i+1
            status = pod.status
            phase = status.phase 
            host_ip = status.host_ip
            pod_ip = status.pod_ip
            
            pod_info = {"create_time":create_time,"namespace":namespace,"pod_ip":pod_ip,"node":host_ip,"status":phase,"affinity":affinity}
            others={"image_pull_secrets":image_pull_secrets,"restart_policy":restart_policy,"node_selector":node_selector,\
                "service_account_name":service_account_name,"host_network":host_network}
            
            mypod = {"name":name,"pod_info":pod_info,\
                    "others":others,"container_info":container_info,\
                    "readiness_probe":readiness_probe,"resources":resources,"volume_mounts":volume_mounts,\
                    "env":env
                }            

            pod_list.append(mypod)
        i = i + 1
    # return json.dumps(pod_list,default=lambda obj: obj.__dict__,indent=4)
    return json.dumps(pod_list,indent=4,cls=MyEncoder)
# from flask_k8s.util import *
def simple_error_handle(msg):
    return jsonify({"error":msg})

@k8s.route('/get_pod_detail_by_name',methods=('GET','POST'))
def get_pod_detail_by_name():
    print("您已进入get_pod_detail_by_name,有什么能帮助您呢?")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace =  handle_input(data.get("namespace"))
    pod_name = handle_input(data.get('pod_name'))
    myclient = client.CoreV1Api()
    field_selector="metadata.name={}".format(pod_name)
    print(field_selector)
    pods = myclient.list_namespaced_pod(namespace=namespace,field_selector=field_selector)
    
    pod = None
    for item in pods.items:
        if item.metadata.name == pod_name:
            pod = item
            break
    if pod == None:
        return simple_error_handle("找不到pod相关信息")

    meta = pod.metadata
    name = meta.name
    create_time = time_to_string(meta.creation_timestamp)
    cluster_name = meta.cluster_name

    pod_labels = meta.labels
    namespace = meta.namespace 
    
    spec = pod.spec
    node_affinity = pod_affinity = pod_anti_affinity = None
    affinity = spec.affinity
    if affinity:
        node_affinity = affinity.node_affinity
        pod_affinity = affinity.pod_affinity
        pod_anti_affinity = affinity.pod_anti_affinity
    host_network = spec.host_network
    image_pull_secrets = spec.image_pull_secrets
    node_selector = spec.node_selector
    restart_policy = spec.restart_policy
    security_context = spec.security_context
    service_account_name = spec.service_account_name
    tolerations = spec.tolerations
    containers = spec.containers
    volumes = spec.volumes
    containers = spec.containers
    init_containers = spec.init_containers

    status = pod.status
    phase = status.phase 
    host_ip = status.host_ip
    pod_ip = status.pod_ip
    
    mypod = {
        "name":name,
        "namespace":namespace,
        "node":host_ip,
        "pod_ip":pod_ip,
        "pod_labels":pod_labels,
        "status":phase,
        "create_time":create_time,
        # spec关键信息
        "affinity":affinity,
        "nodeAffinity":node_affinity,
        "podAffinity":pod_affinity,
        "podAntiAffinity":pod_anti_affinity,
        "hostNetwork":host_network,
        "imagePullSecrets":image_pull_secrets,
        "nodeSelector":node_selector,
        "restartPolicy":restart_policy,
        "serviceAccountName":service_account_name,
        # "terminationGracePeriodSeconds":terminationGracePeriodSeconds,
        "tolerations":tolerations,
        "volumes":volumes,
        # 容器信息
        "containers":containers,
        #初始化容器
        "initContainers":init_containers,
    }          
    # return json.dumps(pod,default=lambda obj: obj.__dict__,indent=4)
    # return jsonify(pod)
    return json.dumps(mypod,indent=4,cls=MyEncoder)
    
@k8s.route('/get_pod_list_v2',methods=('GET','POST'))
def get_pod_list_v2():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all": 
        pods = myclient.list_pod_for_all_namespaces(watch=False)
    else:
        pods = myclient.list_namespaced_pod(namespace=namespace,watch=False)
    i = 0
    pod_list = []
    for pod in pods.items:
        if (i >=0):
            # print(pod)
            meta = pod.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            labels = meta.labels
            namespace = meta.namespace 
            spec = pod.spec
            # tolerations = spec.tolerations
            containers = spec.containers
            container_name = image = ""
            i = 0
            for c in containers: 
                if (i==0):
                    container_name = c.name
                    image = c.image
                i = i+1
            status = pod.status
            phase = status.phase 
            # host_ip = status.host_ip
            node = spec.node_name
            pod_ip = status.pod_ip
            restart_count = None
            if status.container_statuses:
                restart_count = status.container_statuses[0].restart_count
            mypod = {"name":name,"namespace":namespace,"node":node,"pod_ip":pod_ip,"status":phase,"image":image,"restart_count":restart_count,"create_time":create_time}         
            pod_list.append(mypod)
        i = i + 1
    return json.dumps(pod_list,indent=4,cls=MyEncoder)

@k8s.route('/get_pod_list_v3',methods=('GET','POST'))
def get_pod_list_v3():
    data = json.loads(request.get_data().decode("utf-8"))
    # namespace = data.get("namespace").strip()
    node = handle_input(data.get('node'))
    if not node:
        return simple_error_handle("必须要node参数")
    myclient = client.CoreV1Api()
    # 在客户端筛选属于某个node的pod
    pods = myclient.list_pod_for_all_namespaces(watch=False)

    pod_list = []
    for pod in pods.items:
        node_name = pod.spec.node_name
        if node_name == node:
            # # print(pod)
            meta = pod.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            labels = meta.labels
            namespace = meta.namespace 
            spec = pod.spec
            # tolerations = spec.tolerations
            containers = spec.containers
            container_name = image = ""
            i = 0
            for c in containers: 
                if (i==0):
                    container_name = c.name
                    image = c.image
                i = i+1
            status = pod.status
            phase = status.phase 
            # host_ip = status.host_ip
            node = spec.node_name
            pod_ip = status.pod_ip
            restart_count = status.container_statuses[0].restart_count
            mypod = {"name":name,"namespace":namespace,"node":node,"pod_ip":pod_ip,"status":phase,"image":image,"restart_count":restart_count,"create_time":create_time}         
            pod_list.append(mypod)
    return json.dumps(pod_list,indent=4,cls=MyEncoder)

@k8s.route('/get_deployment_list',methods=('GET','POST'))
def get_deployment_list():
    # print('get_deployment_list')
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    namespace = data.get("namespace").strip()
    myclient = client.AppsV1Api()
    # print(namespace)
    if namespace == "" or namespace == "all": 
        deployments = myclient.list_deployment_for_all_namespaces(watch=False)
    else:
        deployments = myclient.list_namespaced_deployment(namespace=namespace)
    i = 0
    deployment_list = []
    for deployment in deployments.items:
        if (i>=0):
            # print(deployment)
            meta = deployment.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
            
            spec = deployment.spec
            replicas = spec.replicas
            selector = spec.selector  
            # strategy = spec.strategy
            template = spec.template
            template_labels = template.metadata.labels
            node_affinity = None
            pod_affinity =None 
            pod_anti_affinity = None
            
            template_spec = template.spec 
            affinity = template_spec.affinity
            if affinity:
                node_affinity = affinity.node_affinity
                pod_affinity = affinity.pod_affinity
                pod_anti_affinity = affinity.pod_anti_affinity
            containers = template_spec.containers
            
            container_names = []
            container_images = []
            for container in containers:
                c_name  = container.name 
                c_image = container.image
                container_names.append(c_name)
                container_images.append(c_image)
            containerInfo = {"name":container_names[0],"image":container_images[0]}
            # node_selector = template_spec.node_selector
            tolerations = template_spec.tolerations
            
            status = deployment.status
            ready = "{}/{}".format(status.ready_replicas,status.replicas)
            mystatus = {"replicas":replicas,"ready":ready,"available_replicas":status.available_replicas,\
            "up-to-date":status.updated_replicas,"create_time":create_time}

            info = {"namespace":namespace,"labels":labels,"container":containerInfo}
            
            mydeployment = {"name":name,"status":mystatus,"info":info,"tolerations":tolerations,"node_affinity":node_affinity,\
                            "pod_affinity":pod_affinity,"pod_anti_affinity":pod_anti_affinity}
            
            deployment_list.append(mydeployment)
            
        i = i +1   
    return json.dumps(deployment_list,indent=4,cls=MyEncoder)
    # return json.dumps(deployment_list,indent=4,cls=MyEncoder)
    # return json.dumps(deployment_list,default=lambda obj: obj.__dict__,indent=4)

@k8s.route('/get_daemonset_list',methods=('GET','POST'))
def get_daemonset_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.AppsV1Api()
    # daemonsets = myclient.list_daemon_set_for_all_namespaces()
    if namespace == "" or namespace == "all": 
        daemonsets = myclient.list_daemon_set_for_all_namespaces(watch=False)
    else:
        daemonsets = myclient.list_namespaced_daemon_set(namespace=namespace)
    i = 0
    
    daemonset_list = []
    for daemonset in daemonsets.items:
        if (i>=0):
            print(daemonset)
            meta = daemonset.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            namespace = meta.namespace      
            spec = daemonset.spec
            template = spec.template
            template_spec = template.spec 
            affinity = template_spec.affinity
            containers = template_spec.containers
            container_list = []
            i = 0 
            for container in containers:
                if (i == 0):
                    image = container.image
                    volume_mounts = container.volume_mounts
                    env = container.env
                    mycontainer = {"image":image}
                    # mycontainer = {"image":image,"volume_mounts":volume_mounts,"env":env}
                    container_list.append(mycontainer)
                i = i + 1
            host_network = template_spec.host_network
            node_selector = template_spec.node_selector
            
            tolerations = template_spec.tolerations
            
            status = daemonset.status
            mystatus = {"current_number_scheduled":status.current_number_scheduled,"desired_number_scheduled":status.desired_number_scheduled,\
                "number_available":status.number_available,"number_ready":status.number_ready,"number_misscheduled":status.number_misscheduled}
            
            mydaemonset = {"name":name,"namespace":namespace,"labels":labels,"affinity":affinity,"containers":container_list,\
                "host_network":host_network,"status":mystatus,"create_time":create_time}
            daemonset_list.append(mydaemonset)
            
        i = i +1       
    return json.dumps(daemonset_list,indent=4,cls=MyEncoder)

@k8s.route('/get_node_name_list',methods=('GET','POST'))
def get_node_name_list():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    
    node_name_list = []
    for node in nodes.items:
        name = node.metadata.name
        node_name_list.append(name)
    return json.dumps(node_name_list,indent=4)


@k8s.route('/get_node_detail_list',methods=('GET','POST'))
def get_node_detail_list():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    i = 0
    node_list = []
    cluster_cpu = 0
    cluster_cpu_usage = 0
    cluster_memory = 0
    cluster_memory_usage = 0
    
    for node in nodes.items:
        if (i>=0):
            # print(node)
            meta = node.metadata
            name = meta.name
            node_usage = get_named_node_usage_detail(name)
            node_cpu_usage = node_usage.get('cpu')
            node_memory_usage = node_usage.get('memory')

            create_time = time_to_string(meta.creation_timestamp)
            labels = meta.labels
            role = labels.get('kubernetes.io/role')
            
            spec = node.spec
            pod_cidr = spec.pod_cidr
            taints = spec.taints
            schedulable = True if spec.unschedulable == None else False
            
            status = node.status
            address = status.addresses[0].address 
            
            capacity = status.capacity
            cpu_num = str_to_int(capacity['cpu'])

            disk_space = handle_disk_space(capacity['ephemeral-storage'])
            memory = handle_memory(capacity['memory'])
            pods = capacity['pods']
            cpu_usage_percent = (node_cpu_usage/1000)/cpu_num * 100
            memory_usage_percent = node_memory_usage/memory * 100
            cpu_detail = "{}/{} {}%".format(float('%.2f' % (node_cpu_usage/1000)), cpu_num,float('%.2f' % cpu_usage_percent))
            memory_detail = "{}/{} {}%".format(math.ceil(node_memory_usage),memory,float('%.2f' % memory_usage_percent))
            images_num = len(status.images)
            mycapacity = {"cpu_detail":cpu_detail,"memory_detail":memory_detail,"storage(G)":disk_space,"pods":pods,"image_num":images_num}
            node_info = status.node_info
   
            mynode = {"name":name,"role":role,"taints":taints,"capacity(cpu(c),memory(Mi))":mycapacity,"labels":labels,"pod_cidr":pod_cidr,\
                "schedulable":schedulable,"create_time":create_time}
            node_list.append(mynode)
        i = i + 1 

    return json.dumps(node_list,indent=4,cls=MyEncoder)

@k8s.route('/get_cluster_stats',methods=('GET','POST'))
def get_cluster_stats():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    i = 0
    node_list = []
    cluster_cpu = 0
    cluster_cpu_usage = 0
    cluster_memory = 0
    cluster_memory_usage = 0
    cluster_disk_cap = 0 
    cluster_pod_cap = 0
    cluster_stat_list = []
    for node in nodes.items:
        if (i>=0):
            # print(node)
            meta = node.metadata
            name = meta.name
            node_usage = get_named_node_usage_detail(name)
            node_cpu_usage = node_usage.get('cpu')
            node_memory_usage = node_usage.get('memory')
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            role = labels.get('kubernetes.io/role')
            print(role)
            
            spec = node.spec
            schedulable = True if spec.unschedulable == None else False
            
            status = node.status
            
            capacity = status.capacity
            cpu_num = str_to_int(capacity['cpu'])
            disk_space = handle_disk_space(capacity['ephemeral-storage'])
            memory = handle_memory(capacity['memory'])
            pods = str_to_int(capacity['pods'])
            
            cpu_usage_percent = (node_cpu_usage/1000)/cpu_num * 100
            memory_usage_percent = node_memory_usage/memory * 100
            cpu_detail = "{}/{} {}%".format(float('%.2f' % (node_cpu_usage/1000)), cpu_num,float('%.2f' % cpu_usage_percent))
            memory_detail = "{}/{} {}%".format(math.ceil(node_memory_usage),memory,float('%.2f' % memory_usage_percent))
            images_num = len(status.images)
            # mycapacity = {"cpu_detail":cpu_detail,"memory_detail":memory_detail,"storage(G)":disk_space,"pods":pods,"image_num":images_num}
            mycapacity = {"cpu":cpu_num,"storage(G)":disk_space,"memory(Mi)":memory,"pods":pods}
            node_info = status.node_info
            
            if schedulable == True:
                cluster_cpu = cluster_cpu + cpu_num
                cluster_memory = cluster_memory + math.ceil(memory)
                cluster_cpu_usage = cluster_cpu_usage + node_cpu_usage/1000
                cluster_memory_usage = cluster_memory_usage + node_memory_usage
                cluster_disk_cap = cluster_disk_cap + disk_space
                cluster_pod_cap = cluster_pod_cap + pods
                
            mynode = {"name":name,"role":role,"capacity(cpu(c),memory(Mi))":mycapacity,\
                "schedulable":schedulable,"create_time":create_time}
            
            node_list.append(mynode)
        i = i + 1
        
    cluster_cpu_usage_percent = cluster_cpu_usage/cluster_cpu * 100
    cluster_memory_usage_percent = cluster_memory_usage/cluster_memory * 100
    cluster_cpu_detail = "{}/{} {}%".format(float('%.2f' % (cluster_cpu_usage)), cluster_cpu,float('%.2f' % cluster_cpu_usage_percent))
    cluster_memory_detail = "{}/{} {}%".format(math.ceil(cluster_memory_usage),cluster_memory,float('%.2f' % cluster_memory_usage_percent))
    cluster_capacity = {"cluster_cpu_detail":cluster_cpu_detail,"cluster_memory_detail":cluster_memory_detail}
    cluster_stat =  {"cluster_cpu_detail":cluster_cpu_detail,"cluster_memory_detail":cluster_memory_detail,"cluster_disk_cap":cluster_disk_cap,"cluster_pod_cap":cluster_pod_cap}
    cluster_stat_list.append(cluster_stat)
    return json.dumps({"node_list":node_list,"cluster_stat_list":cluster_stat_list})

@k8s.route('/get_configmap_list',methods=('GET','POST'))
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
    

@k8s.route('/get_cm_detail_by_name',methods=('GET','POST'))        
def get_cm_detail_by_name():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("收到的数据:{}".format(data))
    namespace =  handle_input(data.get("namespace"))
    cm_name = handle_input(data.get('name'))
    myclient = client.CoreV1Api()
    field_selector="metadata.name={}".format(cm_name)
    current_app.logger.debug(field_selector)
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
@k8s.route('/get_secret_list',methods=('GET','POST'))
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

@k8s.route('/get_secret_detail_by_name',methods=('GET','POST'))        
def get_secret_detail_by_name():
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
    # print(type(data),data)
    data_list = []
    for k,v in data.items():
        # print(k, my_decode(v))
        value = my_decode(v)
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

#列出job
@k8s.route('/get_job_list',methods=('GET','POST'))
def get_job_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.BatchV1Api()
    if namespace == "" or namespace == "all": 
        jobs = myclient.list_job_for_all_namespaces(watch=False)
    else:
        jobs = myclient.list_namespaced_job(namespace=namespace)
    # myclient = client.BatchV1Api()
    # jobs = myclient.list_job_for_all_namespaces()
    job_list = []
    i = 0 
    for job in jobs.items:
        if (i >=0):
            # print(job)
            meta = job.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
                   
            status = job.status
            active = status.active
            succeeded = status.succeeded
            start_time = time_to_string(status.start_time)
            completion_time = time_to_string(status.completion_time)
            
            mystatus = {"active":active,"succeeded":succeeded,"start_time":start_time,"completion_time":completion_time}
            
            myjob = {"name":name,"create_time":create_time,"cluster_name":cluster_name,"labels":labels,"namespace":namespace,"status":mystatus}    
            job_list.append(myjob) 
        i = i +1
    return json.dumps(job_list,indent=4,cls=MyEncoder)

#列出job
@k8s.route('/get_cronjob_list',methods=('GET','POST'))
def get_cronjob_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.BatchV1beta1Api()
    if namespace == "" or namespace == "all": 
        cronjobs = myclient.list_cron_job_for_all_namespaces(watch=False)
    else:
        cronjobs = myclient.list_namespaced_cron_job(namespace=namespace)
    cronjob_list = []
    i = 0 
    for cronjob in cronjobs.items:
        if (i >=0):
            # print(cronjob)
            meta = cronjob.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
            
            spec = cronjob.spec
            schedule = spec.schedule
            successful_jobs_history_limit = spec.successful_jobs_history_limit
            suspend = spec.suspend
            status = cronjob.status
            active = status.active
            last_schedule_time = time_to_string(status.last_schedule_time)
            
            mystatus = {"active":active,"last_schedule_time":last_schedule_time}
            
            mycronjob = {"name":name,"create_time":create_time,"schedule":schedule,"labels":labels,"namespace":namespace,"status":mystatus,\
                "successful_jobs_history_limit":successful_jobs_history_limit, "suspend":suspend}    
            cronjob_list.append(mycronjob) 
        i = i +1
    return json.dumps(cronjob_list,indent=4,cls=MyEncoder)

#列出storageclass
@k8s.route('/get_storageclass_list',methods=('GET','POST'))
def get_storageclass_list():
    myclient = client.StorageV1Api()
    storageclasss = myclient.list_storage_class()
    storageclass_list = []
    i = 0 
    for sc in storageclasss.items:
        if (i >= 0):
            # print(sc)
            meta = sc.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            annotations = meta.annotations
            mount_options = sc.mount_options
            parameters = sc.parameters
            provisioner = sc.provisioner
            reclaim_policy = sc.reclaim_policy
            
            volume_binding_mode = sc.volume_binding_mode
            mysc = {"name":name,"provisioner":provisioner,"reclaim_policy":reclaim_policy,\
                            "parameters":parameters,\
                            "mount_options":mount_options,"volume_binding_mode":volume_binding_mode,"create_time":create_time}    
            storageclass_list.append(mysc) 
        i = i +1
    return json.dumps(storageclass_list,indent=4,cls=MyEncoder)

def takeCreateTime(elem):
    return elem['create_time']
#列出pv
@k8s.route('/get_pv_list',methods=('GET','POST'))
def get_pv_list():
    myclient = client.CoreV1Api()
    pvs = myclient.list_persistent_volume()
    pv_list = []
    i = 0 
    for pv in pvs.items:
        if (i >= 0):
            # print(pv)
            meta = pv.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
 
            spec = pv.spec
            
            access_modes = spec.access_modes[0]
            capacity = spec.capacity['storage']
            nfs = spec.nfs
            cephfs = spec.cephfs
            flexVolume = spec.flex_volume
            glusterfs = spec.glusterfs
            rbd = spec.rbd
            hostPath = spec.host_path
            
            source = None
            if nfs:
                source=nfs
            elif hostPath:
                source=hostPath
            elif rbd:
                source=rbd
            elif flexVolume:
                source = flexVolume
            elif glusterfs:
                source = glusterfs
            else:
                pass
            
            mountOptions = spec.mount_options
            pv_reclaim_policy = spec.persistent_volume_reclaim_policy
            storage_class_name = spec.storage_class_name
            volume_mode = spec.volume_mode
            claim_ref = spec.claim_ref
            pvc_namespace = pvc_name = None
            if claim_ref:
                pvc_namespace = claim_ref.namespace
                pvc_name = claim_ref.name
            pvc = "{}/{}".format(pvc_namespace,pvc_name)

            status = pv.status.phase

            # volume_binding_mode = pv.volume_binding_mode
            mypv = {"name":name,"pvc":pvc,"capacity":capacity,"status":status,"access_modes":access_modes,"pv_reclaim_policy":pv_reclaim_policy, \
                    "storage_class_name":storage_class_name,"source":source,
                   "volume_mode":volume_mode,"create_time":create_time}   

            pv_list.append(mypv) 
        i = i +1
    return json.dumps(pv_list,indent=4,cls=MyEncoder)

#列出pvc
@k8s.route('/get_pvc_list',methods=('GET','POST'))
def get_pvc_list():
    
    # myclient = client.CoreV1Api()
    # pvcs = myclient.list_persistent_volume_claim_for_all_namespaces()
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all": 
        pvcs = myclient.list_persistent_volume_claim_for_all_namespaces(watch=False)
    else:
        pvcs = myclient.list_namespaced_persistent_volume_claim(namespace=namespace)
    pvc_list = []
    i = 0 
    for pvc in pvcs.items:
        if (i >= 0):
            # print(pvc)
            meta = pvc.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            namespace = meta.namespace
 
            spec = pvc.spec
            
            access_modes = spec.access_modes[0]
            resources = spec.resources
            capacity = resources.requests['storage']
            storage_class_name = spec.storage_class_name
            volume_name = spec.volume_name

            # status = pvc.status
            phase = pvc.status.phase
            # volume_binding_mode = pvc.volume_binding_mode
            mypvc = {"name":name,"pv":volume_name,"status":phase,"capacity":capacity,"resources":resources,"namespace":namespace,\
                    "access_modes":access_modes,"storage_class_name":storage_class_name,"create_time":create_time}   

            pvc_list.append(mypvc) 
        i = i +1
    return json.dumps(pvc_list,indent=4,cls=MyEncoder)

@k8s.route('/get_statefulset_list',methods=('GET','POST'))
def get_statefulset_list():
    myclient = client.AppsV1Api()
    statefulsets = myclient.list_stateful_set_for_all_namespaces()
    i = 0
    statefulset_list = []
    for statefulset in statefulsets.items:
        if (i>=0):
            # print(statefulset)
            meta = statefulset.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace      
            spec = statefulset.spec
            template = spec.template
            template_spec = template.spec 
            
            replicas = spec.replicas
            # selector = spec.selector
            service_name = spec.service_name
            # update_strategy = spec.update_strategy
            # affinity = template_spec.affinity
            containers = template_spec.containers
            container_list = []
            for container in containers:
                image = container.image
                volume_mounts = container.volume_mounts
                env = container.env
                mycontainer = {"image":image,"volume_mounts":volume_mounts,"env":env}
                container_list.append(mycontainer)
            host_network = template_spec.host_network
            # node_selector = template_spec.node_selector
            
            tolerations = template_spec.tolerations
            
            pvc_list = []
            pvc_templates = spec.volume_claim_templates
            for pvc_template in pvc_templates:    
                pvc_annotations= pvc_template.metadata.annotations
                pvc_name = pvc_template.metadata.name
                pvc_access_mode = pvc_template.spec.access_modes[0]
                pvc_capacity = pvc_template.spec.resources.requests['storage']
                pvc_status = pvc_template.status.phase
                my_pvc = {"pvc_name":pvc_name,"pvc_access_mode":pvc_access_mode,"pvc_capacity":pvc_capacity,"pvc_status":pvc_status,"pvc_annotations":pvc_annotations}
                pvc_list.append(my_pvc)

            
            mystatefulset = {"name":name,"create_time":create_time,"namespace":namespace,"labels":labels,"replicas":replicas,"service_name":service_name,"container_list":container_list,\
                "host_network":host_network,"tolerations":tolerations,"pvc_list":pvc_list}
            statefulset_list.append(mystatefulset)
            
        i = i +1       
    return json.dumps(statefulset_list,indent=4,cls=MyEncoder)

#列出ingress
@k8s.route('/get_ingress_list',methods=('GET','POST'))
def get_ingress_list():
    # myclient = client.ExtensionsV1beta1Api()
    # # /apis/extensions/v1beta1/namespaces/{namespace}/ingresses
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = handle_input(data.get("namespace"))
    myclient = client.ExtensionsV1beta1Api()
    if namespace == "" or namespace == "all": 
        ingresss = myclient.list_ingress_for_all_namespaces(watch=False)
    else:
        ingresss = myclient.list_namespaced_ingress(namespace=namespace)
    ingress_list = []
    i = 0 
    for ingress in ingresss.items:
        if (i >=0):
            # print(ingress)
            meta = ingress.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
            
            spec = ingress.spec
            rules = spec.rules
            domain_list = []
            for rule in rules:
                domain = rule.host
                domain_list.append(domain)
            
            tls = spec.tls
            
            myingress = {"name":name,"namespace":namespace,\
                "domain_list":domain_list,"rule":rule,"tls":tls,"create_time":create_time}    
            ingress_list.append(myingress) 
        i = i +1
    return json.dumps(ingress_list,indent=4,cls=MyEncoder)

@k8s.route('/get_deployment_name_list',methods=('GET','POST'))
def get_deployment_name_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = handle_input(data.get("namespace"))
    myclient = client.AppsV1Api()
    if namespace == "" or namespace == "all": 
        deployments = myclient.list_deployment_for_all_namespaces(watch=False)
    else:
        deployments = myclient.list_namespaced_deployment(namespace=namespace)
    deployment_names = []
    for deployment in deployments.items:
        name = deployment.metadata.name
        deployment_names.append(name)
    return json.dumps(deployment_names)

@k8s.route('/get_virtualservice_name_list',methods=('GET','POST'))
def get_virtualservice_name_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    print(namespace)
    if namespace == "" or namespace == "all": 
        virtualservices = myclient.list_cluster_custom_object(group="networking.istio.io",
                                                          version="v1alpha3",
                                                          plural="virtualservices")
    else:
        virtualservices = myclient.list_namespaced_custom_object(group="networking.istio.io",
                                                          version="v1alpha3",
                                                          plural="virtualservices",
                                                          namespace=namespace)
    print(type(virtualservices['items']))
    virtualservice_names = []
    for virtualservice in virtualservices['items']:
        name = virtualservice['metadata']['name']
        virtualservice_names.append(name)
    return json.dumps(virtualservice_names)