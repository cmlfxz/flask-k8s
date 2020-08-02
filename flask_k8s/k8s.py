from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from dateutil import tz, zoneinfo
from datetime import datetime,date
from .k8s_decode import MyEncoder
import json,os,math,requests,time,pytz,ssl,yaml
from .util import get_db_conn,my_decode,my_encode,str_to_int,str_to_float
from .util import SingletonDBPool
from .util import time_to_string,utc_to_local
from .util import dir_path
from .util import handle_input,handle_toleraion_seconds,string_to_int,handle_toleration_item
from .util import get_cluster_config,simple_error_handle
from .util import handle_cpu,handle_memory,handle_disk_space
from .k8s_pod import get_pod_num_by_node
from kubernetes import client,config
from kubernetes.client.rest import ApiException

k8s = Blueprint('k8s',__name__,url_prefix='/api/k8s')

CORS(k8s, supports_credentials=True, resources={r'/*'})

# from flask_opentracing import FlaskTracer
# from .util import init_tracer
#
# tracing = FlaskTracer(tracer=init_tracer('flask-k8s.ms-dev'))
@k8s.after_request
def after(resp):
    # print("after is called,set cross")
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name,user,user_id,X-B3-TraceId,X-B3-SpanId,X-B3-Sampled'
    return resp

def takename(e):
    return e['name']
def takeCreateTime(elem):
    return elem['create_time']

# http://192.168.11.51:1900/apis/metrics.k8s.io/v1beta1/nodes 

@k8s.before_app_request
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

def get_named_node_usage_detail(name):
    myclient = client.CustomObjectsApi()
    plural = "{}/{}".format("nodes",name)
    current_app.logger.debug(plural)
    # 这个API不稳定
    node_usage = {}
    #bug当有节点没开，获取不到数据，页面会出不来数据，退而求其次，获取不到，置0
    try:
        node = myclient.list_cluster_custom_object(group="metrics.k8s.io",version="v1beta1",plural=plural)
        node_name = node['metadata']['name']
        cpu = handle_cpu(node['usage']['cpu'])
        memory = handle_memory(node['usage']['memory'])
        node_usage = {"node_name":node_name,"cpu":cpu,"memory":memory}
    except ApiException as e:
        if isinstance(e.body,dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            message = e.body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        current_app.logger.debug(msg)
        node_usage = {"node_name":name,"cpu":0,"memory":0}
         
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

#列出gateway
@k8s.route('/get_gateway_list',methods=('GET','POST'))
def get_gateway_list():
    # myclient = client.CustomObjectsApi()
    # obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="gateways")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="gateways")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace,group="networking.istio.io",version="v1alpha3",plural="gateways")
    except ApiException as e:
        if isinstance(e.body,dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            body = e.body
            message = body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})
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
    #bug 没有vs的集群报错404，页面没具体显示
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="virtualservices")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace,group="networking.istio.io",version="v1alpha3",plural="virtualservices")
    except ApiException as e:
        if isinstance(e.body,dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            body = e.body
            message = body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})

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
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="destinationrules")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace,group="networking.istio.io",version="v1alpha3",plural="destinationrules")
    except ApiException as e:
        if isinstance(e.body,dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            body = e.body
            message = body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})
    #obj是一个字典
    drs = obj['items']
    dr_list = []
    i = 0
    for dr in drs:
        if(i>=0):
            # print(dr)
            meta = dr['metadata'] 
            spec = dr['spec']
            name = meta['name']
            namespace = meta['namespace']
            time_str= meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')

            host = spec['host']
            subsets = None
            if 'subsets' in spec.keys():
                subsets = spec['subsets']
            trafficPolicy = None
            if 'trafficPolicy' in spec.keys():
                trafficPolicy = spec['trafficPolicy']
            my_dr = {}
            my_dr = {"name":name,"namespace":namespace,"host":host,"subsets":subsets}
            my_dr['trafficPolicy'] = trafficPolicy
            my_dr['create_time'] = create_time
            dr_list.append(my_dr)
            
        i = i + 1
    return json.dumps(dr_list,indent=4,cls=MyEncoder)

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
# @tracing.trace()
def get_namespace_name_list():
    current_app.logger.debug("get_namespace_name_list接收到的header:{}".format(request.headers))
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
# @tracing.trace()
def get_node_name_list():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    
    node_name_list = []
    for node in nodes.items:
        name = node.metadata.name
        node_name_list.append(name)
    return json.dumps(node_name_list,indent=4)

def format_float(num):
    return  float("%.2f" % num)

# def format_percent(num):
#     return "{}%".format(float("%.2f" % num))

def create_single_node_detail_obj(node,simple):
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
    # 获取单独node的性能数据
    node_usage = get_named_node_usage_detail(name)
    # 100m 转成 0.12 已核为单位
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

    pod_detail = "{}/{} {}%".format(node_pod_num, pod_total, pod_usage_percent)
    cpu_detail = "{}/{} {}%".format(node_cpu_usage, cpu_total, cpu_usage_percent)
    memory_detail = "{}/{} {}%".format(node_memory_usage, memory_total, memory_usage_percent)

    mycapacity = {}
    mycapacity["cpu_detail"] = cpu_detail
    mycapacity["memory_detail"] = memory_detail
    mycapacity["pod_detail"] = pod_detail
    mycapacity["storage"] = disk_space
    mycapacity["image_num"] = image_num

    mynode = {}
    mynode["name"] = name
    mynode["role"] = role
    
    mynode["schedulable"] = schedulable
    if not simple:
        mynode["node_capacity"] = mycapacity
        #CPU总量
        mynode["cpu_total"]= cpu_total
        #CPU使用量
        mynode["cpu_usage"]= node_cpu_usage
        #CPU百分比
        mynode["cpu_usage_percent"] = cpu_usage_percent
        #内存部分
        mynode["memory_total"]= memory_total
        mynode["memory_usage"]= node_memory_usage
        mynode["memory_usage_percent"]= memory_usage_percent
        #pod部分
        mynode["pod_total"] = pod_total
        mynode["pod_num"] = node_pod_num
        mynode["pod_usage_percent"] = pod_usage_percent
        mynode["storage"] = disk_space
    else:
        mynode['node_info'] = node_info
        mynode["taints"] = taints
        mynode["capacity(cpu(c),memory(Mi),storage(G))"] = mycapacity
        mynode["labels"] = labels
        mynode["pod_cidr"] = pod_cidr 
    mynode["create_time"] = create_time
    return mynode

#节点列表页面使用
@k8s.route('/get_node_detail_list',methods=('GET','POST'))
def get_node_detail_list():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    i = 0
    node_list = []
    for node in nodes.items:
        if (i>=0):
            # print(node)
            mynode = create_single_node_detail_obj(node,simple=True)
            node_list.append(mynode)
        i = i + 1
    return json.dumps(node_list,indent=4,cls=MyEncoder)

# 集群详情页面使用
@k8s.route('/get_node_detail_list_v2',methods=('GET','POST'))
def get_node_detail_list_v2():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    node_list = []
    for node in nodes.items:
        mynode = create_single_node_detail_obj(node,simple=False)
        node_list.append(mynode)
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
    cluster_pod_usage= 0
    cluster_stat_list = []
    for node in nodes.items:
        if (i>=0):
            # print(node)
            meta = node.metadata
            name = meta.name
            schedulable = True if node.spec.unschedulable == None else False
            # 统计集群信息
            if schedulable == True:
                spec = node.spec
                # 获取单独node的性能数据
                node_usage = get_named_node_usage_detail(name)
                # 100m 转成 0.12 已核为单位
                node_cpu_usage = format_float(node_usage.get('cpu') / 1000)
                current_app.logger.debug("node_cpu_usage:{}".format(node_cpu_usage))
                node_memory_usage = node_usage.get('memory')
                node_pod_num = get_pod_num_by_node(name)

                capacity = node.status.capacity
                # 搜集数量
                cpu_total = str_to_int(capacity['cpu'])
                memory_total = handle_memory(capacity['memory'])
                pod_total = str_to_int(capacity['pods'])
                disk_space = handle_disk_space(capacity['ephemeral-storage'])

                # 集群CPU总数
                cluster_cpu = cluster_cpu + cpu_total
                # 集群CPU使用量
                cluster_cpu_usage = cluster_cpu_usage + node_cpu_usage
                current_app.logger.debug("cluster_cpu_usage:{}".format(cluster_cpu_usage))
                #集群内存总量
                cluster_memory = cluster_memory + memory_total
                #集群内存使用量
                cluster_memory_usage = cluster_memory_usage + node_memory_usage
                #磁盘总量
                cluster_disk_cap = cluster_disk_cap + disk_space
                #集群pod总量
                cluster_pod_cap = cluster_pod_cap + pod_total
                #集群pod数量
                cluster_pod_usage= cluster_pod_usage+ node_pod_num
        i = i + 1
        
    cluster_cpu_usage_percent = format_float(cluster_cpu_usage/cluster_cpu * 100)
    cluster_cpu_usage = format_float(cluster_cpu_usage)
    cluster_cpu_detail = "{}/{} {}%".format(cluster_cpu_usage, cluster_cpu,cluster_cpu_usage_percent)

    cluster_memory_usage_percent = format_float(cluster_memory_usage/cluster_memory * 100)
    cluster_memory_detail = "{}/{} {}%".format(cluster_memory_usage,cluster_memory,cluster_memory_usage_percent)

    cluster_pod_usage_percent = format_float(cluster_pod_usage/cluster_pod_cap * 100)
    cluster_pod_detail = "{}/{} {}%".format(cluster_pod_usage,cluster_pod_cap,cluster_pod_usage_percent)

    cluster_stat = {}
    cluster_stat["cpu_detail"] = cluster_cpu_detail
    cluster_stat["memory_detail"] = cluster_memory_detail
    cluster_stat["pod_detail"] = cluster_pod_detail
    cluster_stat["disk_cap"] = cluster_disk_cap


    # CPU详情
    cluster_stat["cpu_total"] = cluster_cpu
    cluster_stat["cpu_usage"] = cluster_cpu_usage
    cluster_stat["cpu_usage_percent"] = cluster_cpu_usage_percent
    #内存详情
    cluster_stat["memory_total"] = cluster_memory
    cluster_stat["memory_usage"] = cluster_memory_usage
    cluster_stat["memory_usage_percent"] = cluster_memory_usage_percent
    #POD详情
    cluster_stat["pod_total"] = cluster_pod_cap
    cluster_stat["pod_usage"] = cluster_pod_usage
    cluster_stat["pod_usage_percent"] = cluster_pod_usage_percent

    cluster_stat_list.append(cluster_stat)
    return json.dumps(cluster_stat_list,indent=4,cls=MyEncoder)
    # return json.dumps({"cluster_stat_list":cluster_stat_list})

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
    # current_app.logger.debug(type(data),data)
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
            
            myjob = {"name":name,"namespace":namespace,"status":mystatus,"labels":labels,"create_time":create_time}
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
            
            mycronjob = {"name":name,"namespace":namespace,"schedule":schedule,"status":mystatus,"labels":labels,\
                "successful_jobs_history_limit":successful_jobs_history_limit, "suspend":suspend,"create_time":create_time}
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

            info = {}
            info["capacity"] = capacity
            info["access_modes"] = access_modes
            info["pv_reclaim_policy"] = pv_reclaim_policy
            info["volume_mode"] = volume_mode

            my_pv = {}
            my_pv["name"] = name
            my_pv["pvc"] = pvc
            my_pv["status"] = status
            my_pv["info"] = info
            my_pv["storage_class_name"] = storage_class_name
            my_pv["source"] = source
            my_pv["create_time"] = create_time

            pv_list.append(my_pv) 
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
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = handle_input(data.get("namespace"))
    current_app.logger.debug("接收到的数据:{}".format(namespace))
    myclient = client.AppsV1Api()
    # statefulsets = myclient.list_stateful_set_for_all_namespaces()
    try:
        if namespace == "" or namespace == "all":
            statefulsets = myclient.list_stateful_set_for_all_namespaces()
        else:
            statefulsets = myclient.list_namespaced_stateful_set(namespace=namespace)
    except ApiException as e:
        if isinstance(e.body,dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            body = e.body
            message = body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})

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
            #bug TypeError: 'NoneType' object is not iterable
            if pvc_templates != None:
                for pvc_template in pvc_templates:    
                    pvc_annotations= pvc_template.metadata.annotations
                    pvc_name = pvc_template.metadata.name
                    pvc_access_mode = pvc_template.spec.access_modes[0]
                    pvc_capacity = pvc_template.spec.resources.requests['storage']
                    pvc_status = pvc_template.status.phase
                    my_pvc = {"pvc_name":pvc_name,"pvc_access_mode":pvc_access_mode,"pvc_capacity":pvc_capacity,"pvc_status":pvc_status,"pvc_annotations":pvc_annotations}
                    pvc_list.append(my_pvc)

            info = {}
            info["replicas"] = replicas
            info["labels"] = labels
            info["service_name"] = service_name
            info["host_network"] = host_network
            info["tolerations"] = tolerations
            
            my_state = {}
            my_state["name"] = name
            my_state["namespace"] = namespace
            my_state["info"] = info
            my_state["container_list"] =container_list
            my_state["pvc_list"] = pvc_list
            my_state["create_time"] = create_time
            
            statefulset_list.append(my_state)
            
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

@k8s.route('/get_hpa_list',methods=('GET','POST'))
def get_hpa_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.AutoscalingV1Api()
    if namespace == "" or namespace == "all":
        hpas = myclient.list_horizontal_pod_autoscaler_for_all_namespaces()
    else:
        hpas =myclient.list_namespaced_horizontal_pod_autoscaler(namespace=namespace)
    print(type(hpas.items))
    hpa_list = []
    for hpa in hpas.items:
        # print(hpa)
        meta  = hpa.metadata
        name = meta.name
        namespace = meta.namespace
        spec = hpa.spec
        maxReplicas = spec.max_replicas
        minReplicas = spec.min_replicas
        scaleTargetRef = spec.scale_target_ref
        targetCPUUtilizationPercentage = spec.target_cpu_utilization_percentage

        myhpa= {}
        myhpa["name"] =name
        myhpa["namespace"] =namespace
        myhpa["minReplicas"] =minReplicas

        myhpa["maxReplicas"] =maxReplicas

        myhpa["scaleTargetRef"] =scaleTargetRef
        myhpa["targetCPUUtilizationPercentage"] =targetCPUUtilizationPercentage

        print(myhpa)
        hpa_list.append(myhpa)
    # return json.dumps({"ok":"123"})
    return json.dumps(hpa_list,indent=4,cls=MyEncoder)

def format_time(dt):
    tz_sh = pytz.timezone('Asia/Shanghai')
    now= datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nowstamp = time.mktime(time.strptime(now, '%Y-%m-%d %H:%M:%S'))
    dtime = dt.astimezone(tz_sh).strftime("%Y-%m-%d %H:%M:%S")
    dstamp = time.mktime(dt.astimezone(tz_sh).timetuple())
    difftime = nowstamp - dstamp
    d = int(difftime/24/60/60)
    hour = int(difftime/60/60)
    m = int(difftime/60)
    s = int(difftime%60)
    if d > 0:
        t = "{}d{}h".format(d,hour)
    elif hour > 0:
        t = "{}h{}m".format(hour,m)
    elif m > 0:
        t = "{}m{}s".format(m,s)
    else:
        t = "{}s".format(s)
    print(t)

    return t

@k8s.route('/get_event_list',methods=('GET','POST'))
def get_event_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("event接收的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all":
        events = myclient.list_event_for_all_namespaces()
    else:
        events =myclient.list_namespaced_event(namespace=namespace)
    i = 0
    event_list = []
    for event in events.items:
        if (i >= 0):
            # print(event)
            io = event.involved_object
            meta = event.metadata
            source = event.source.component
            count = event.count
            # first_time = format_time(event.first_timestamp)
            # last_time = format_time(event.last_timestamp)
            first_time = time_to_string(event.first_timestamp)
            last_time = time_to_string(event.last_timestamp)
            message = event.message
            reason = event.reason
            type = event.type
            kind = io.kind
            subobject  = io.name
            # namespace = io.namespace
            object = "{}/{}".format(kind, subobject)
            name = meta.name
            namespace = meta.namespace
            my_event = {}
            my_event["name"] = name
            my_event["namespace"] =namespace
            my_event["last_seen"] = last_time
            my_event["message"] = message
            my_event["reason"] =reason
            my_event["type"] =type
            my_event["object"] =object
            my_event["source"] =source

            # my_event["first_seen"] =first_time

            event_list.append(my_event)
            # print(event_list)

        i= i+1
    return json.dumps(event_list,indent=4,cls=MyEncoder)
    # return jsonify({"ok":"get event list"})

@k8s.route('/get_component_status_list',methods=('GET','POST'))
def get_component_status_list():
    # data = json.loads(request.get_data().decode("utf-8"))
    # current_app.logger.debug("event接收的数据:{}".format(data))
    # namespace = handle_input(data.get("namespace"))
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


