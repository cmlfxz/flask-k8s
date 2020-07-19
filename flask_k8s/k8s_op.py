from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
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

from kubernetes import client,config
from kubernetes.client.rest import ApiException
from kubernetes.client.models.v1_namespace import V1Namespace

k8s_op = Blueprint('k8s_op',__name__,url_prefix='/k8s_op')

CORS(k8s_op, suppors_credentials=True, resources={r'/*'})
@k8s_op.after_request
def after(resp):
    # print("after is called,set cross")
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name'
    return resp

@k8s_op.before_app_request
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
            print(type(result),result)
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

@k8s_op.route('/create_namespace', methods=('GET', 'POST'))
def create_namespace():
    data = json.loads(request.get_data().decode('utf-8'))
    # {"project_name": "ms", "env_name": "dev", "cluster_name": "k8s_c1", "istio_inject": "on"}
    print("接收到的数据:{}".format(data))
    project_name = handle_input(data.get('project_name'))
    env_name = handle_input(data.get('env_name'))
    name = "{}-{}".format(project_name,env_name)
    print(name)
    labels = {}
    istio_inject = handle_input(data.get('istio_inject'))
    print("istio_inject:{}".format(istio_inject))
    if istio_inject:
        labels['istio-injection'] = "enabled"
    else:
        labels = None
    print("labels:{}".format(labels))
    return create_namespace_resource(name=name,labels=labels)

@k8s_op.route('/delete_namespace', methods=('GET', 'POST'))
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

@k8s_op.route('/delete_pv', methods=('GET', 'POST'))
def delete_pv():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    myclient = client.CoreV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_persistent_volume(name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除PVC异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_op.route('/delete_pvc', methods=('GET', 'POST'))
def delete_namespaced_service():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace  = handle_input(data.get('namespace'))
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.CoreV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_persistent_volume_claim(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除PV异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

# @k8s_op.route('/get_node_by_name', methods=('GET', 'POST'))
def get_node_by_name(name=None):
    params = {}
    params['label_selector'] = {"kubernetes.io/role": "master"}
    # field_selector='metadata.name=192.168.11.52'
    # label_selector="kubernetes.io/role=master"
    # name = "192.168.11.52"
    field_selector="{}={}".format("metadata.name",name)
    # pretty=True
    # limit=3
    node = None
    node_list = client.CoreV1Api().list_node(limit=1,field_selector=field_selector)
    print(type(node_list),len(node_list.items))
    # node = node_list.items
    # i = 0
    for item in node_list.items:
        if item.metadata.name == name:
            node = item
            break

    print(type(node))
    return node

@k8s_op.route('/update_node', methods=('GET', 'POST'))
def update_node():
    data=json.loads(request.get_data().decode('utf-8'))
    print("update_node接收到的数据是{}".format(data))
    name=handle_input(data.get("node_name"))
    action=handle_input(data.get("action"))
    
    node  = get_node_by_name(name)
    if node == None:
        return jsonify({"error":"找不到此node信息"})
    if action=="add_taint":
        print("正在添加node污点")
        effect = handle_input(data.get('taint_effect'))
        key = handle_input(data.get('taint_key'))   
        value = handle_input(data.get('taint_value'))
        print(type(node.spec.taints))
        if node.spec.taints == None:
            node.spec.taints = []
        taint = client.V1Taint(effect=effect,key=key,value=value)
        node.spec.taints.append(taint)
        print(node.spec.taints)
    elif action=="delete_taint":
        print("正在删除node污点")
        effect = handle_input(data.get('taint_effect'))
        key = handle_input(data.get('taint_key'))
        value = handle_input(data.get('taint_value'))
        print(key,value)
        print(type(node.spec.taints))
        if node.spec.taints == None:
            return jsonify({"error":"taint列表为空"})
        # 查找元素
        i = -1
        taint_len = len(node.spec.taints)
        has_taint = False
        for taint in node.spec.taints:
            i = i + 1
            print(taint)
            if effect == taint.effect and key==taint.key and value ==taint.value:
                has_taint = True
                break
        #查找元素
        if not has_taint:
            return jsonify({"error": "没有此taint"})
        else:
            node.spec.taints.pop(i)
            print(node.spec.taints)
    elif action=="update_taint":
        print("正在更新node污点")
        old_effect = handle_input(data.get('old_taint_effect'))
        old_key = handle_input(data.get('old_taint_key'))
        old_value = handle_input(data.get('old_taint_value'))
        new_effect = handle_input(data.get('taint_effect'))
        new_key = handle_input(data.get('taint_key'))
        new_value = handle_input(data.get('taint_value'))
        
        if node.spec.taints == None:
            node.spec.taints = []
        new_taint = client.V1Taint(effect=new_effect,key=new_key,value=new_value)
        print(new_taint)
        # 思路，找到index，替换
        # 查找元素
        i = -1
        taint_len = len(node.spec.taints)
        has_taint = False
        for taint in node.spec.taints:
            i = i + 1
            print(taint)
            if old_effect == taint.effect and old_key==taint.key and old_value ==taint.value:
                has_taint = True
                break
        #查找元素
        if not has_taint:
            return jsonify({"error": "没有此taint"})
        else:
            node.spec.taints[i] = new_taint
            print(node.spec.taints)
    #增加标签
    elif action == "add_labels":
        current_app.logger.debug("正在执行:{}".format(action))
        #{"a":1,"b":2}
        input_labels = handle_input(data.get('labels'))
        current_app.logger.debug("接收到的数据:{}".format(input_labels))
        if input_labels == None:
            return simple_error_handle("没有收到labels")
        labels = node.metadata.labels
        current_app.logger.debug(type(labels),labels)
        for k, v in input_labels.items():
            labels[k] = v
        node.metadata.labels = labels
    elif action == "delete_labels":
        current_app.logger.debug("正在执行:{}".format(action))
        #{"a":1,"b":2}
        input_labels = handle_input(data.get('labels'))
        current_app.logger.debug("接收到的数据:{}".format(input_labels))
        if input_labels == None:
            return simple_error_handle("没有收到labels")
        labels = node.metadata.labels
        current_app.logger.debug(type(labels),labels)
        for k, v in input_labels.items():
            labels.pop(k)
        current_app.logger.debug("移除标签后:{}".format(labels))
        node.metadata.labels = labels
    else:
        return jsonify({"error":"不支持此动作{}".format(action)})
    try:
        if action == "delete_labels":
            result = client.CoreV1Api().replace_node(name=name, body=node)
        else:
            result = client.CoreV1Api().patch_node(name=name,body=node)
    except ApiException as e:
        body = json.loads(e.body)
        msg = {"status": e.status, "reason": e.reason, "message": body['message']}
        return jsonify({'error': '更新node失败', "msg": msg})

    return jsonify({"ok": "{}成功".format(action)})

def get_namespace_by_name(name):
    # namespaces = client.AppsV1Api().list_namespaced_namespace(namespace=namespace)
    namespaces = client.CoreV1Api().list_namespace()
    namespace = None
    for ns in namespaces.items:
        if ns.metadata.name == name:
            namespace = ns
            break
    return namespace

# 已经废弃，根据名字获取命名空间对象
@k8s_op.route('/get_namespace_object',methods=('GET','POST'))
def get_namespace_object():
    # namespaces = client.AppsV1Api().list_namespaced_namespace(namespace=namespace)
    data = json.loads(request.get_data().decode('utf-8'))
    print("get_namespace_object接收到的数据：{}".format(data))
    name = handle_input(data.get('name'))
    namespaces = client.CoreV1Api().list_namespace()
    namespace = None
    for ns in namespaces.items:
        if ns.metadata.name == name:
            namespace = ns
            break
    # print(namespace.to_dict())
    # print(namespace.to_str())
    # 转化失败
    return namespace.to_str()

@k8s_op.route('/update_namespace', methods=('GET', 'POST'))
def update_namespace():
    # {"name": name, "labels": labels, "action": "remove_istio_inject"}
    data = json.loads(request.get_data().decode('utf-8'))
    print("update_namespace接收到的数据：{}".format(data))
    name = handle_input(data.get('name'))
    namespace = get_namespace_by_name(name)
    if not namespace:
        return jsonify({"error":"找不到此名称空间"})
    labels = json.loads(handle_input(data.get('labels')))
    # print(labels)
    if labels == None:
        labels = {}
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
        # print(result)
        # print(result.status)
    except Exception as e:
        print(e)
        return jsonify({"error":"更新命名空间出现异常"})
    return jsonify({"ok":"更新命名空间成功"})

def create_pv_object(name,**kwargs):
    for k,v in kwargs.items():
        print ('Optional key: %s value: %s' % (k, v))
    capacity = kwargs['capacity']
    accessModes = kwargs['accessModes']
    reclaimPolicy = kwargs['reclaimPolicy']
    storage_class_name = kwargs['storage_class_name']
    nfs = kwargs['nfs']
    # current_app.logger.debug("nfs: {}".format(nfs))
    nfs_path = nfs['path']
    nfs_server = nfs['server']
    readonly = nfs['readonly']
    
    nfs_readonly = False
    if readonly == 'true':
        nfs_readonly = True
    elif readonly == 'false':
        nfs_readonly == False
    else:
        pass
    spec = client.V1PersistentVolumeSpec(
        access_modes = [accessModes],
        capacity = {"storage":capacity},
        persistent_volume_reclaim_policy = reclaimPolicy,
        nfs = client.V1NFSVolumeSource(
            path = nfs_path,
            server = nfs_server,
            read_only = nfs_readonly
        ),
        storage_class_name=storage_class_name,
    )
    print(spec)
    pv = client.V1PersistentVolume(
        api_version="v1",
        kind="PersistentVolume",
        metadata=client.V1ObjectMeta(name=name),
        spec=spec)
    return pv

@k8s_op.route('/create_pv',methods=('GET','POST'))
def create_pv():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))

    pv =  handle_input(data.get('pv'))
    capacity = pv['capacity']
    accessModes = pv['accessModes']
    reclaimPolicy = pv['reclaimPolicy']
    storage_class_name = pv['storage_class_name']
    nfs  = pv['nfs']

    pv = create_pv_object(name=name,capacity=capacity,accessModes=accessModes,\
            reclaimPolicy=reclaimPolicy,storage_class_name=storage_class_name,nfs=nfs)
    current_app.logger.debug(pv)
    myclient = client.CoreV1Api()
    try:
        api_response = myclient.create_persistent_volume(body=pv)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '创建失败',"msg":msg})
    
    return jsonify({"ok":"创建pv成功"})

def create_service(namespace,service_name,type,selector,port,target_port):
    myclient = client.CoreV1Api()
    body = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(
            name=service_name
        ),
        spec=client.V1ServiceSpec(
            type=type,
            selector=selector,
            ports=[client.V1ServicePort(
                port=port,
                target_port=target_port
            )]
        )
    )
    myclient.create_namespaced_service(namespace=namespace, body=body)

def delete_service(namespace,service_name):
    myclient = client.CoreV1Api()
    myclient.delete_namespaced_service(name=service_name,namespace=namespace)
    
def create_ingress(namespace,ingress_name,host,path,service_name,service_port):
    body = client.NetworkingV1beta1Ingress(
        api_version="networking.k8s.io/v1beta1",
        kind="Ingress",
        metadata=client.V1ObjectMeta(name=ingress_name,
                                     annotations='{"kubernetes.io/ingress.class": "nginx"}'),
        spec=client.NetworkingV1beta1IngressSpec(
            rules=[client.NetworkingV1beta1IngressRule(
                host=host,
                http=client.NetworkingV1beta1HTTPIngressRuleValue(
                    paths=[client.NetworkingV1beta1HTTPIngressPath(
                        path=path,
                        backend=client.NetworkingV1beta1IngressBackend(
                            service_port=servcie_port,
                            service_name=service_name)
                    )]
                )
            )]
        )
    )
    myclient = client.AppsV1Api().NetworkingV1beta1Api()
    myclient.create_namespaced_ingress(namespace=namespace, body=body)

def delete_ingress(ingress_name,namespace):
    myclient = client.AppsV1Api().NetworkingV1beta1Api()
    myclient.delete_namespaced_ingress(
        name=ingress_name,
        namespace=namespace
    )

def get_vs_by_name(namespace,vs_name):
    virtual_services = client.CustomObjectsApi().list_namespaced_custom_object(group="networking.istio.io",
                                                                               version="v1alpha3",
                                                                               plural="virtualservices",namespace=namespace)
    virtual_service = None
    for vs in virtual_services['items']:
        if vs['metadata']['name'] == vs_name:
            virtual_service = vs
            break 
    return virtual_service
            
def update_virtual_service(vs_name,namespace,prod_weight,canary_weight):
    myclient = client.CustomObjectsApi()
    #先获取到对应的vs名称
    vs = get_vs_by_name(namespace,vs_name)
    if vs == None:
        return jsonify({"error":"1003","msg":"找不到该vs"})
    # print(vs)
    #这样必须规定第一条route是生产版本，第二条是灰度版本
    # print(vs['spec']['http'][0]['route'][0]['weight'])
    # print(vs['spec']['http'][0]['route'][1]['weight'])
    try:
        vs['spec']['http'][0]['route'][0]['weight'] = prod_weight
        vs['spec']['http'][0]['route'][1]['weight'] = canary_weight
        api_response = myclient.patch_namespaced_custom_object( group="networking.istio.io",
                                                                version="v1alpha3",
                                                                plural="virtualservices",
                                                                name=vs_name,
                                                                namespace=namespace,
                                                                body=vs)
        # print(api_response['spec'])
        status="{}".format(api_response['spec']['http'])
    except Exception as e:
        print(e)
        return jsonify({"异常":"可能非生产环境，没有设置灰度"})

    return jsonify({"update_status":status})

@k8s_op.route('/update_vs',methods=('GET','POST'))
def update_vs():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("接受到的数据:{}".format(data))
    namespace = handle_input(data.get('namespace'))
    vs_name = handle_input(data.get('vs_name'))
    print(type(data.get('canary_weight')))
    canary_weight = math.ceil( str_to_int(handle_input(data.get('canary_weight'))))
    if(canary_weight < 0 or canary_weight > 100):
        return jsonify({"error":1003,"msg":"灰度值需在1-100之间"})
    prod_weight = 100 - canary_weight
    return update_virtual_service(vs_name=vs_name,namespace=namespace,prod_weight=prod_weight,canary_weight=canary_weight)

def delete_virtual_service(namespace,virtual_service_name=None):
    myclient = client.CustomObjectsApi()
    api_response = myclient.delete_namespaced_custom_object(group="networking.istio.io",
                                                            version="v1alpha3",
                                                            plural="virtualservices",
                                                            namespace=namespace,
                                                            name=virtual_service_name,
                                                            body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5))

    # print(api_response)
    result="{}".format(api_response)
    return jsonify({"update_status":result})

@k8s_op.route('/delete_vs',methods=('GET','POST'))
def delete_vs():
    data = json.loads(request.get_data().decode('UTF-8'))
    current_app.logger.debug("接受到的数据:{}".format(data))
    namespace = handle_input(data.get('namespace'))
    virtual_service_name = handle_input(data.get('virtual_service_name'))
    return delete_virtual_service(namespace=namespace,virtual_service_name=virtual_service_name)

@k8s_op.route('/delete_daemonset',methods=('GET','POST'))
def delete_daemonset():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))
    
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.AppsV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_daemon_set(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除daemonset异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_op.route('/delete_statefulset',methods=('GET','POST'))
def delete_statefulset():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))
    
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.AppsV1beta1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_stateful_set(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除statefulset异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_op.route('/delete_configmap',methods=('GET','POST'))
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

@k8s_op.route('/delete_secret', methods=('GET', 'POST'))
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

@k8s_op.route('/delete_hpa', methods=('GET', 'POST'))
def delete_hpa():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.AutoscalingV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_horizontal_pod_autoscaler(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除hpa异常',"msg":msg})
    return jsonify({"ok":"删除成功"})


@k8s_op.route('/delete_job', methods=('GET', 'POST'))
def delete_job():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.BatchV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_job(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除job异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s_op.route('/delete_cronjob', methods=('GET', 'POST'))
def delete_cronjob():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.BatchV1beta1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_cron_job(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除cronjob异常',"msg":msg})
    return jsonify({"ok":"删除成功"})