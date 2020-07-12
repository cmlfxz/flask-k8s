from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from kubernetes import client,config
from dateutil import tz, zoneinfo
import json,os
from datetime import datetime,date
import math
from .k8s_decode import MyEncoder,DateEncoder
import requests
import time 
import pytz
import ssl
import yaml
import math
from kubernetes.client.rest import ApiException
from .util import get_db_conn,my_decode,my_encode,str_to_int,str_to_float
from .util import SingletonDBPool
from .util import time_to_string,utc_to_local
from .util import dir_path
from .util import handle_input,handle_toleraion_seconds,string_to_int,handle_toleration_item
from .util import simple_error_handle
from flask_cors import *
from kubernetes.client.models.v1_namespace import V1Namespace

k8s_op = Blueprint('k8s_op',__name__,url_prefix='/k8s_op')

CORS(k8s_op, suppors_credentials=True, resources={r'/*'})


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

@k8s_op.after_request
def after(resp):
    # print("after is called,set cross")
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name'
    return resp

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
    else:
        return jsonify({"error":"不支持此动作{}".format(action)})
    try:
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

@k8s_op.route('/create_deploy_by_yaml', methods=('GET', 'POST'))
def create_deploy_by_yaml():
    if request.method == "POST":
        data = request.get_data()
        json_data = json.loads(data.decode("utf-8"))
        yaml_name = json_data.get("yaml_name")
        if yaml_name == None or yaml_name == "":
            msg = "需要提供yaml文件"
            return jsonify({"error": "1001", "msg": msg})
        yaml_dir = os.path.join(dir_path, "yaml")
        file_path = os.path.join(yaml_dir, yaml_name)
        if not os.path.exists(file_path):
            msg = "找不到此文件{}".format(file_path)
            return jsonify({"error": "1001", "msg": msg})

        with open(file_path, encoding='utf-8') as f:
            cfg = f.read()
            obj = yaml.safe_load(cfg)  # 用load方法转字典
            try:
                myclient = client.AppsV1Api()
                resp = myclient.create_namespaced_deployment(body=obj, namespace="default")
                # print(resp)
                print("Deployment created. name='%s' " % resp.metadata.name)
            except ApiException as e:
                return make_response(json.dumps({"error": "1001", "msg": str(e)}, indent=4, cls=MyEncoder), 1001)

    return jsonify({"msg": "创建deployment成功"})

# for k, v in kwargs.items():
#         print ('Optional argument %s (kwargs): %s' % (k, v))
# if claim_ref is not None:
#     self.claim_ref = claim_ref
# if flex_volume is not None:
#     self.flex_volume = flex_volume
# if glusterfs is not None:
#     self.glusterfs = glusterfs
# if host_path is not None:
#     self.host_path = host_path
# if local is not None:
#     self.local = local
# if mount_options is not None:
#     self.mount_options = mount_options
# if persistent_volume_reclaim_policy is not None:
#     self.persistent_volume_reclaim_policy = persistent_volume_reclaim_policy
# if rbd is not None:
#     self.rbd = rbd
# if storage_class_name is not None:
#     self.storage_class_name = storage_class_name
# if storageos is not None:
#     self.storageos = storageos
# if volume_mode is not None:
#     # self.volume_mode = volume_mode
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
    
    # current_app.logger.debug(nfs_path)
    # current_app.logger.debug(nfs_server)
    # current_app.logger.debug(nfs_readonly)
    
    # current_app.logger.debug(capacity)
    # current_app.logger.debug(accessModes)
    # current_app.logger.debug(reclaimPolicy)
    # current_app.logger.debug(storage_class_name)
    # current_app.logger.debug(nfs)
    
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
    
    current_app.logger.debug(capacity)
    current_app.logger.debug(nfs)
    
    # args= {"capacity":capacity,"accessModes":accessModes,\
    #         "reclaimPolicy":reclaimPolicy,"storage_class_name":storage_class_name,"nfs":nfs}

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

def create_deployment_object(name=None,namespace=None,image=None,port=None,image_pull_policy=None,\
    imagePullSecret=None,labels=None,replicas=None,cpu=None,memory=None,liveness_probe=None,readiness_probe=None):
    #configure pod template container
    resources = None
    volumeMounts = []
    volumes = []
    if(cpu or memory):
        resources=client.V1ResourceRequirements(
            requests={"cpu": str(int(cpu/2))+"m", "memory": str(int(memory/2))+"Mi"},
            limits={"cpu": str(cpu)+"m", "memory": str(memory)+"Mi"}
        )
    vm1 = client.V1VolumeMount(name='log',mount_path="/opt/microservices/logs")
    volumeMounts.append(vm1)
    v1 = client.V1Volume(name="log",empty_dir=client.V1EmptyDirVolumeSource())
    volumes.append(v1)
    image_pull_secret=client.V1LocalObjectReference(name=imagePullSecret)
    container = client.V1Container(
        name=name,
        image=image,
        image_pull_policy=image_pull_policy,
        ports=[client.V1ContainerPort(container_port=port,name="web",protocol="TCP")],
        resources = resources,
        readiness_probe = readiness_probe,
        liveness_probe = liveness_probe,
        volume_mounts = volumeMounts
        #volume_mounts 
        #env
    )
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels=labels),
        spec=client.V1PodSpec(containers=[container],image_pull_secrets=[image_pull_secret],volumes = volumes)
    )
    spec = client.V1DeploymentSpec(
        replicas=replicas,
        template=template,
        selector={'matchLabels':labels}
        #strategy
    )
    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=name,namespace=namespace),
        spec=spec
    )
    return deployment

def create_deployment(api_instance,deployment,namespace):
    api_response = api_instance.create_namespaced_deployment(namespace=namespace,body=deployment)
    print("Deployment created. status='%s'\n" % str(api_response.status))
    print(api_response)
    return api_response.status

@k8s_op.route('/create_deploy',methods=('GET','POST'))
def create_deploy():
    error = ""
    if request.method == "POST":
        data = request.get_data()
        json_data = json.loads(data.decode("utf-8"))
        project = json_data.get("project").strip()
        environment = json_data.get("environment").strip()
        cluster = json_data.get("cluster").strip()
        
        imageRepo = json_data.get("imageRepo").strip()
        imageName = json_data.get("imageName").strip()
        imageTag = json_data.get("imageTag").strip()
        
        imagePullPolicy = json_data.get("imagePullPolicy").strip()
        imagePullSecret = json_data.get("imagePullSecret").strip()
        containerPort = str_to_int(json_data.get("containerPort").strip())
        replicas = json_data.get("replicas").strip()
        cpu = json_data.get("cpu").strip()
        memory = json_data.get("memory").strip()
        label_key1 = json_data.get("label_key1").strip()
        label_value1 = json_data.get("label_value1").strip()
        label_key2 = json_data.get("label_key2").strip()
        label_value2 = json_data.get("label_value2").strip()

        env = json_data.get("env").strip()
        volumeMount = json_data.get("volumeMount").strip()
        updateType = json_data.get("updateType").strip()
        
        probeType = json_data.get("probeType").strip()
        healthCheck = json_data.get("healthCheck").strip()
        healthPath = json_data.get("healthPath").strip() 
        initialDelaySeconds = str_to_int(json_data.get("initialDelaySeconds").strip())
        periodSeconds = str_to_int(json_data.get("periodSeconds").strip())
        failureThreshold = str_to_int(json_data.get("failureThreshold").strip())
        healthTimeout = str_to_int(json_data.get("healthTimeout").strip())
        healthCmd = json_data.get("healthCmd").strip()
        liveness_probe = None
        readiness_probe = None
        if (healthCheck=="true"):
            if(probeType=="tcp"):
                liveness_probe = client.V1Probe(initial_delay_seconds=initialDelaySeconds,\
                    period_seconds = periodSeconds,\
                    timeout_seconds   = healthTimeout ,\
                    failure_threshold = failureThreshold,\
                    tcp_socket=client.V1TCPSocketAction(port=containerPort))
                readiness_probe = liveness_probe
            elif(probeType=="http"):
                liveness_probe = client.V1Probe(initial_delay_seconds=initialDelaySeconds,\
                    period_seconds = periodSeconds,\
                    timeout_seconds   = healthTimeout ,\
                    failure_threshold = failureThreshold,\
                    http_get=client.V1HTTPGetAction(path=healthPath,port=containerPort))
                readiness_probe = liveness_probe
            elif(probeType=="cmd"):
                pass
            
            else:
                pass
        if(containerPort == 1):
            error = "容器端口不能为空"
        if(imageRepo=="" or project=="" or environment=="" or imageName=="" or imageTag==""):
            error = "镜像相关不能为空"
        if(label_key1== "" or label_value1 == ""):
            error = "label相关数据不能为空（至少输入一对key/value）"
        replicas=str_to_int(replicas) 
        
        cpu = int(1000*(str_to_float(cpu)))
        memory = int(1024*(str_to_float(memory)))
          
        if(error != "" ):
            print(error)
            return jsonify({"error":1002,"msg":error})
        #ms-dev
        namespace = project+"-"+environment
        # myhub.mydocker.com/ms-dev/base:v1.0
        image = imageRepo+"/"+project+"-"+environment+"/"+imageName+":"+imageTag
        labels = { label_key1:label_value1 }    
        if(label_key2 !="" and label_value2 != ""):
            labels[label_key2] = label_value2
        myclient = client.AppsV1Api()
        deployment = create_deployment_object(name=imageName,namespace=namespace,image=image,port=containerPort,\
            image_pull_policy=imagePullPolicy,imagePullSecret=imagePullSecret ,labels=labels,replicas=replicas,cpu=cpu,memory=memory,\
            liveness_probe=liveness_probe,readiness_probe=readiness_probe)
        print(type(deployment))
        to_yaml = yaml.load(json.dumps(deployment,indent=4,cls=MyEncoder))
        file = os.path.join(dir_path,"demo-deployment.yaml")
        stream = open(file,'w')
        yaml.safe_dump(to_yaml,stream,default_flow_style=False)
        status = create_deployment(api_instance=myclient,namespace=namespace,deployment=deployment)
        return json.dumps(deployment,indent=4,cls=MyEncoder)

    return jsonify({'a':1})

def get_deployment_by_name(namespace, deploy_name):
    deployments = client.AppsV1Api().list_namespaced_deployment(namespace=namespace)

    deployment = None
    for deploy in deployments.items:
        if deploy.metadata.name == deploy_name:
            deployment = deploy
            break
    return deployment

def update_deployment(deploy_name,namespace,image=None,replicas=None,pod_anti_affinity_type=None,anti_affinity_key=None,anti_affinity_value=None):
    # '/apis/apps/v1/namespaces/{namespace}/deployments/{name}', 'PATCH'
    print(pod_anti_affinity_type,anti_affinity_key,anti_affinity_value)
    deployment = get_deployment_by_name(namespace,deploy_name)
    if (deployment == None):
        return jsonify({"error":"1003","msg":"找不到该deployment"})
    if image:
        deployment.spec.template.spec.containers[0].image=image
    if replicas:
        deployment.spec.replicas = replicas
    affinity = None
    if pod_anti_affinity_type:
        if pod_anti_affinity_type == "required":
            # anti_affinity_type = "requiredDuringSchedulingIgnoredDuringExecution"
            label_selector = client.V1LabelSelector(match_expressions=[
                                client.V1LabelSelectorRequirement(key=anti_affinity_key,operator='In',values=[anti_affinity_value])
                             ])
            # label_selector = client.V1LabelSelector(match_expressions=[ client.V1LabelSelectorRequirement(key='app',operator=None)])
            # # label_selector = None
            affinity=client.V1Affinity(
                pod_anti_affinity = client.V1PodAntiAffinity(
                    required_during_scheduling_ignored_during_execution=[
                        # client.re V1PreferredSchedulingTerm
                        # client.V1Pod
                        client.V1PodAffinityTerm(
                            label_selector = label_selector,
                            topology_key = 'kubernetes.io/hostname'
                        )
                    ]
                )
            )
            print("{}".format(affinity))
        else:
            pass
    if affinity:
        deployment.spec.template.spec.affinity = affinity
    try:
        ResponseNotReady = client.AppsV1Api().patch_namespaced_deployment(
            name=deploy_name,
            namespace=namespace,
            body=deployment
        )
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '创建失败',"msg":msg})
    
    return jsonify({"ok":"更新deployment成功"})

# '/apis/apps/v1/namespaces/{namespace}/deployments/{name}', 'PATCH'
def update_deployment_v2(deploy_name, namespace, action, image=None, replicas=None,toleration=None, pod_anti_affinity=None,
                         pod_affinity=None, node_affinity=None,labels=None):
    # print(namespace,deploy_name)
    deployment = get_deployment_by_name(namespace, deploy_name)
    # print(deployment)
    if (deployment == None):
        return jsonify({"error": "1003", "msg": "找不到该deployment"})
    if action == "add_pod_anti_affinity":
        if not pod_anti_affinity:
            msg="{}需要提供pod_anti_affinity".format(action)
            return jsonify({"error":msg})
        paa = deployment.spec.template.spec.affinity.pod_anti_affinity
        if paa != None:
            print("pod_anti_affinity已经存在,使用更新模式")
            action = "update_pod_anti_affinity"
            # return jsonify({"error":"pod_anti_affinity已经存在，无法添加"})
        deployment.spec.template.spec.affinity.pod_anti_affinity = pod_anti_affinity
    elif action == "delete_pod_anti_affinity":
        print("正在运行{}操作".format(action))
        deployment.spec.template.spec.affinity.pod_anti_affinity = None
        print(deployment)
    elif action == "add_toleration":
        print("正在运行{}操作".format(action))
        if not toleration:
            msg="{}需要提供toleration".format(action)
            return jsonify({"error":msg})
        t = deployment.spec.template.spec.tolerations
        if t == None:
            t = []
        t.append(toleration)
        deployment.spec.template.spec.tolerations = t
    elif action == "delete_toleration":
        print("正在运行{}操作".format(action))
        if not toleration:
            msg="{}需要提供toleration".format(action)
            return jsonify({"error":msg})
        t = deployment.spec.template.spec.tolerations
        # print("deployment {} toleration删除前:{}".format(deploy_name,t),type(t))
        if t == None:
            return jsonify({"error":"deployment {} toleration为空".format(deploy_name)})
        print(type(toleration),toleration)
        try:
            i = t.index(toleration)
        except ValueError as e:
            print(e)
            return jsonify({"error":"没有此toleration"})
        deployment.spec.template.spec.tolerations.pop(i)
        # return jsonify({"info":i})

    elif action == "add_pod_affinity":
        pass
    elif action == "delete_pod_affinity":
        pass
    elif action == "add_node_affnity":
        pass
    elif action == "delete_node_affnity":
        pass
    elif action == "update_replicas":
        deployment.spec.replicas = replicas
    elif action == "update_image":
        if not image:
            msg="{}需要提供image".format(action)
            return jsonify({"error":msg})
        deployment.spec.template.spec.containers[0].image = image
    elif action == "add_labels":
        pass
    elif action == "delete_labels":
        pass
    else:
        msg="暂时不支持{}操作".format(action)
        print(msg)
        return jsonify({"error":msg})
    try:

        if action == "delete_pod_anti_affinity" or action=="update_pod_anti_affinity":
            print("正在执行替换")
            ResponseNotReady = client.AppsV1Api().replace_namespaced_deployment(
                name=deploy_name,
                namespace=namespace,
                body=deployment
            )
        else:
            ResponseNotReady = client.AppsV1Api().patch_namespaced_deployment(
                name=deploy_name,
                namespace=namespace,
                body=deployment
            )
        
    except ApiException as e:
        print(e)
        body = json.loads(e.body)
        msg = {"status": e.status, "reason": e.reason, "message": body['message']}
        return jsonify({'error': '创建失败', "msg": msg})

    return jsonify({"ok": "deployment 执行{}成功".format(action)})

@k8s_op.route('/update_deploy_v2',methods=('GET','POST'))  
def update_deploy_v2():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("接受到的数据:{}".format(data))
    namespace = handle_input(data.get('namespace'))
    deploy_name = handle_input(data.get('deploy_name'))
    action = handle_input(data.get('action'))
    
    image = None
    replicas=None
    toleration=None
    pod_anti_affinity=None
    pod_affinity=None
    node_affinity=None
    labels=None
    if action == "add_pod_anti_affinity":
        print("正在运行{}操作".format(action))
        affinity = handle_input(data.get('pod_anti_affinity'))
        affinity_type = handle_input(affinity.get('type'))

        labelSelector = handle_input(affinity.get('labelSelector'))
        key = handle_input(affinity.get('key'))
        value = handle_input(affinity.get('value'))

        topologyKey = handle_input(affinity.get('topologyKey'))
        if affinity_type == "required":
            if labelSelector == "matchExpressions":
                if not isinstance(value,list):
                    value = [value]
                operator = handle_input(affinity.get('operator'))
                if operator != 'In' and operator != 'NotIn':
                    value = None
                print(value)
                label_selector = client.V1LabelSelector(match_expressions=[
                    client.V1LabelSelectorRequirement(key=key, operator=operator,
                                                      values=value)
                ])
            elif labelSelector == "matchLabels":
                if isinstance(value,list):
                    return jsonify({"error":"{}模式下不支持values设置为数组".format(labelSelector)})
                label_selector = client.V1LabelSelector(match_labels={key:value})
            else:
                return jsonify({"error":"不支持{} labelSelector".format(labelSelector)})
            client.V1Affinity
            pod_anti_affinity=client.V1PodAntiAffinity(
                required_during_scheduling_ignored_during_execution=[
                    client.V1PodAffinityTerm(
                        label_selector=label_selector,
                        topology_key=topologyKey
                    )
                ]
            )
            print("{}".format(pod_anti_affinity))
        elif affinity_type == "preferred":
            weight = string_to_int(handle_input(affinity.get('weight')))
            if weight == None:
                return jsonify({"error":"{}类型必须设置weight".format(affinity_type)})

            if labelSelector == "matchExpressions":
                if not isinstance(value,list):
                    value = [value]

                operator = handle_input(affinity.get('operator'))
                if operator != 'In' and operator != 'NotIn':
                    value = None
                label_selector = client.V1LabelSelector(match_expressions=[
                    client.V1LabelSelectorRequirement(key=key, operator=operator,
                                                      values=value)
                ])
            elif labelSelector == "matchLabels":
                if isinstance(value,list):
                    return jsonify({"error":"{}模式下不支持values设置为数组".format(labelSelector)})
                label_selector = client.V1LabelSelector(match_labels={key:value})
            else:
                return jsonify({"error": "不支持{} labelSelector".format(labelSelector)})
            pod_anti_affinity=client.V1PodAntiAffinity(
                preferred_during_scheduling_ignored_during_execution=[
                    client.V1WeightedPodAffinityTerm(
                        pod_affinity_term = client.V1PodAffinityTerm(
                            label_selector=label_selector,
                            topology_key=topologyKey
                        ),
                        weight = weight
                    )
                ]
            )
            print("{}".format(pod_anti_affinity))
        else:
            return jsonify({"error":"不支持{}这种调度".format(affinity_type)})
    elif action == "delete_pod_anti_affinity":
        print("正在运行{}操作".format(action))
        pass
    elif action == "add_toleration":
        print("正在运行{}操作".format(action))
        t = handle_input(data.get("toleration"))
        print(type(toleration),toleration)
        
        effect = t.get('effect') 
        key = t.get('key') 
        operator = t.get('operator') 
        value = t.get('value') 
        toleration_seconds = handle_toleraion_seconds(t.get('toleration_seconds'))
        print("toleration_seconds:{}".format(toleration_seconds))
        
        # if (effect != None and key != None and operator != None):
        # toleration = {
        #     "effect":effect,
        #     "key":key,
        #     "operator":operator,
        #     "value":value,
        #     "toleration_seconds":toleration_seconds,
        # }
        toleration = client.V1Toleration(effect=effect,key=key,operator=operator,toleration_seconds=toleration_seconds,value=value)
        print(toleration)
        if not toleration:
            msg = "{}需要提供toleration(effect,key,operator,value,)".format(action)
            return jsonify({"error":msg})            
        
    elif action == "delete_toleration":
        print("正在运行{}操作".format(action))
        t = handle_input(data.get("toleration"))
        effect = handle_toleration_item(t.get('effect') )
        key = handle_toleration_item(t.get('key') )
        operator = handle_toleration_item(t.get('operator') )
        value = handle_toleration_item(t.get('value') )
        toleration_seconds = handle_toleraion_seconds(t.get('toleration_seconds'))
        print("toleration_seconds:{}".format(toleration_seconds))
        
        # if (effect != None and key != None and operator != None):
        toleration = client.V1Toleration(effect=effect,key=key,operator=operator,toleration_seconds=toleration_seconds,value=value)
        if not toleration:
            msg = "{}需要提供toleration(effect,key,operator,value,)".format(action)
            return jsonify({"error":msg})    
    elif action == "add_pod_affinity":
        pass
    elif action == "delete_pod_affinity":
        pass
    elif action == "add_node_affnity":
        pass
    elif action == "delete_node_affnity":
        pass
    elif action == "update_replicas":
        replicas = handle_input(data.get('replicas'))
        if not replicas:
            msg = "{}需要提供replicas".format(action)
            return jsonify({"error":msg})
    elif action == "update_image":
        project = handle_input(data.get('project'))
        env = handle_input(data.get('env'))
        imageRepo = handle_input(data.get('imageRepo'))
        imageName = handle_input(data.get('imageName'))
        imageTag = handle_input(data.get('imageTag'))
        if (imageRepo != None and project != None and env != None and imageName != None and imageTag != None):
            image = "{}/{}-{}/{}:{}".format(imageRepo, project, env, imageName, imageTag)
        print("image值{}".format(image))
        if not image:
            msg = "{}需要提供image".format(action)
            return jsonify({"error":msg})
    elif action == "add_labels":
        pass
    elif action == "delete_labels":
        pass
    else:
        msg = "暂时不支持{}操作".format(action)
        print(msg)
        return jsonify({"error": msg})
    return update_deployment_v2(deploy_name=deploy_name, namespace=namespace, action=action, image=image, replicas=replicas,toleration=toleration, pod_anti_affinity=pod_anti_affinity,
        pod_affinity=pod_affinity, node_affinity=node_affinity,labels=labels)

@k8s_op.route('/update_deploy',methods=('GET','POST'))  
def update_deploy():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("接受到的数据:{}".format(data))
    namespace = handle_input(data.get('namespace'))
    deploy_name =handle_input(data.get('deploy_name'))
    replicas = handle_input(data.get('replicas'))
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

def delete_deployment(namespace,deploy_name=None):
    api_response =  client.AppsV1Api().delete_namespaced_deployment(
        name=deploy_name,
        namespace=namespace,
        body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
    )
    # print("Deployment deleted. status='%s'\n" % str(api_response.status))
    status="{}".format(api_response.status)
    return jsonify({"update_status":status})

@k8s_op.route('/delete_deploy',methods=['POST'])  
def delete_deploy():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("delete_deploy接受到的数据:{}".format(data))
    namespace = data.get('namespace').strip()
    deploy_name = data.get('deploy_name').strip()
    return delete_deployment(deploy_name=deploy_name,namespace=namespace)

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
    print("delete_deploy接受到的数据:{}".format(data))
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
