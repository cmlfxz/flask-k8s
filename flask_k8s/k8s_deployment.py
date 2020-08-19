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
from .util import error_with_status
from .k8s_op import get_event_list_by_name
from kubernetes import client,config
from kubernetes.client.rest import ApiException
from kubernetes.client.models.v1_namespace import V1Namespace

k8s_deployment = Blueprint('k8s_deployment',__name__,url_prefix='/api/k8s/deployment')
CORS(k8s_deployment, supports_credentials=True, resources={r'/*'})

@k8s_deployment.after_request
def after(resp):
    # print("after is called,set cross")
    resp = make_response(resp)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS,PATCH,DELETE'
    resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type,cluster_name,user,user_id'
    return resp

@k8s_deployment.before_app_request
def load_header():
    if request.method == 'OPTIONS':
        pass
    if request.method == 'POST':
        try:
            cluster_name = request.headers.get('cluster_name')
            user = request.headers.get('user')
            print("集群名字:{},user:{}".format(cluster_name,user))
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
    # print("Deployment created. status='%s'\n" % str(api_response.status))
    # print(api_response)
    return api_response.status

@k8s_deployment.route('/create_deploy',methods=('GET','POST'))
def create_deploy():
    error = ""
    if request.method == "POST":
        data = json.loads(request.get_data().decode("utf-8"))
        project = data.get("project").strip()
        environment = data.get("environment").strip()
        cluster = data.get("cluster").strip()
        
        imageRepo = data.get("imageRepo").strip()
        imageName = data.get("imageName").strip()
        imageTag = data.get("imageTag").strip()
        
        imagePullPolicy = data.get("imagePullPolicy").strip()
        imagePullSecret = data.get("imagePullSecret").strip()
        containerPort = str_to_int(data.get("containerPort").strip())
        replicas = data.get("replicas").strip()
        cpu = data.get("cpu").strip()
        memory = data.get("memory").strip()
        label_key1 = data.get("label_key1").strip()
        label_value1 = data.get("label_value1").strip()
        label_key2 = data.get("label_key2").strip()
        label_value2 = data.get("label_value2").strip()

        env = data.get("env").strip()
        volumeMount = data.get("volumeMount").strip()
        updateType = data.get("updateType").strip()
        
        probeType = data.get("probeType").strip()
        healthCheck = data.get("healthCheck").strip()
        healthPath = data.get("healthPath").strip() 
        initialDelaySeconds = str_to_int(data.get("initialDelaySeconds").strip())
        periodSeconds = str_to_int(data.get("periodSeconds").strip())
        failureThreshold = str_to_int(data.get("failureThreshold").strip())
        healthTimeout = str_to_int(data.get("healthTimeout").strip())
        healthCmd = data.get("healthCmd").strip()
        
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
            # print(error)
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
        # print(type(deployment))
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

def update_deployment_v2(deploy_name, namespace, action, image=None, replicas=None,toleration=None,node_affinity=None, pod_anti_affinity=None,
                         pod_affinity=None,labels=None):
    current_app.logger.debug("命名空间:{},deploy_name: {}".format(namespace,deploy_name))
    deployment = get_deployment_by_name(namespace, deploy_name)
    # print(deployment)
    if (deployment == None):
        # return jsonify({"error": "1003", "msg": "找不到该deployment"})
        return error_with_status(error="找不到该deployment",msg="",code=1003)
    if action == "add_pod_anti_affinity":
        if not pod_anti_affinity:
            msg="{}需要提供pod_anti_affinity".format(action)
            # return jsonify({"error":msg})
            return error_with_status(error="", msg=msg, code=1003)
        # 修复affinity为空的bug
        affinity = deployment.spec.template.spec.affinity
        if  not affinity:
            affinity = client.V1Affinity(pod_anti_affinity = pod_anti_affinity)
            deployment.spec.template.spec.affinity = affinity
        # 修复affinity为空的bug
        else:
            print("pod_anti_affinity已经存在,使用更新模式")
            action = "update_affinity"
            deployment.spec.template.spec.affinity.pod_anti_affinity = pod_anti_affinity
    elif action == "delete_pod_anti_affinity":
        print("正在运行{}操作".format(action))
        affinity = deployment.spec.template.spec.affinity
        if not affinity:
            return simple_error_handle("还没设置亲和性")
        pod_anti_affinity = affinity.pod_anti_affinity
        if not pod_anti_affinity:
            return simple_error_handle("还没设置互斥调度")
        deployment.spec.template.spec.affinity.pod_anti_affinity = None
        print("删除互斥调度后")
        print(deployment.spec.template.spec.affinity)
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
    elif action == "add_node_affinity":
        # current_app.logger.debug(node_affinity)
        if not node_affinity:
            # return simple_error_handle("{}需要提供node_affinity".format(action))
            msg = "{}需要提供node_affinity".format(action)
            return simple_error_handle(msg=msg, code=1003)
        # 修复affinity为空的bug
        affinity = deployment.spec.template.spec.affinity
        current_app.logger.debug("添加前affinity:    "+json.dumps(affinity,cls=MyEncoder))
        current_app.logger.debug("即将添加node_affinity:    " + json.dumps(node_affinity, cls=MyEncoder))
        if  not affinity:
            affinity = client.V1Affinity(node_affinity = node_affinity)
            deployment.spec.template.spec.affinity = affinity
        # 修复affinity为空的bug
        else:
            print("affinity已经存在,使用更新模式")
            action = "update_affinity"
            deployment.spec.template.spec.affinity.node_affinity = node_affinity
    elif action == "delete_node_affinity":
        current_app.logger.debug("正在运行{}操作".format(action))
        affinity = deployment.spec.template.spec.affinity
        if not affinity:
            return simple_error_handle("还没设置亲和性")
        node_affinity = affinity.node_affinity
        if not node_affinity:
            return simple_error_handle("还没设置互斥调度")
        deployment.spec.template.spec.affinity.node_affinity = None
        print("删除节点亲和性后")
        print(deployment.spec.template.spec.affinity)
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
        return simple_error_handle("暂时不支持{}操作".format(action))
    try:
        print(action)
        if action == "delete_pod_anti_affinity" or action=="delete_node_affinity" or action == "update_affinity":
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
        return error_with_status(error="创建失败",msg=msg,status=1000)

    return jsonify({"ok": "deployment 执行{}成功".format(action)})

@k8s_deployment.route('/update_deploy_v2',methods=('GET','POST'))  
def update_deploy_v2():
    data = json.loads(request.get_data().decode('UTF-8'))
    current_app.logger.debug("接受到的数据:{}".format(data))
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
            print("添加的互斥调度为:{}".format(pod_anti_affinity))
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
            print("添加的互斥调度为:{}".format(pod_anti_affinity))
        else:
            return jsonify({"error":"不支持{}这种调度".format(affinity_type)})
    elif action == "delete_pod_anti_affinity":
        print("正在运行{}操作".format(action))
        pass
    elif action == "add_node_affinity":
        current_app.logger.debug("正在运行{}操作".format(action))
        affinity = handle_input(data.get('node_affinity'))
        node_affinity_type = handle_input(affinity.get('type'))

        nodeSelector = handle_input(affinity.get('nodeSelector'))
        key = handle_input(affinity.get('key'))
        value = handle_input(affinity.get('value'))
        operator = handle_input(affinity.get('operator'))
        values = []
        if operator == 'Exists' or operator == 'DoesNotExist':
            values == None
        else:
            if not isinstance(value, list):
                values.append(value)
            else:
                values = value

        if node_affinity_type == "preferred":
            weight = string_to_int(handle_input(affinity.get('weight')))
            if weight == None:
                return simple_error_handle("{}类型必须设置weight".format(node_affinity_type))
            preferred_term = []
            if nodeSelector == "matchExpressions":
                match_expressions = []
                expression = client.V1NodeSelectorRequirement(
                        key = key,
                        operator = operator,
                        values = values,
                )
                match_expressions.append(expression)
                preference = client.V1NodeSelectorTerm(
                    match_expressions = match_expressions
                )
            # nodeSelector == "matchFields"
            else :
                match_fields = []
                field = client.V1NodeSelectorRequirement(
                        key=key,
                        operator=operator,
                        values=values,
                )
                match_fields.append(field)
                preference = client.V1NodeSelectorTerm(
                    match_fields = match_fields
                )
            term =  client.V1PreferredSchedulingTerm(
                        weight=weight,
                        preference=preference,
                    )
            preferred_term.append(term)
            node_affinity = client.V1NodeAffinity(
                #直接append
                preferred_during_scheduling_ignored_during_execution = preferred_term
            )
        elif node_affinity_type == "required":
            current_app.logger.debug("node_affinity_type:{}".format(node_affinity_type))
            node_selector_terms = []
            if nodeSelector == "matchExpressions":
                match_expressions = []
                expression = client.V1NodeSelectorRequirement(
                        key = key,
                        operator = operator,
                        values = values,
                )
                match_expressions.append(expression)
                term = client.V1NodeSelectorTerm(
                    match_expressions = match_expressions
                )
            else:
                match_fields = []
                field = client.V1NodeSelectorRequirement(
                        key = key,
                        operator = operator,
                        values = values,
                )
                match_fields.append(field)

                term = client.V1NodeSelectorTerm(
                    match_fields = match_fields
                )
            node_selector_terms.append(term)
            node_affinity = client.V1NodeAffinity(
                required_during_scheduling_ignored_during_execution = client.V1NodeSelector(
                    node_selector_terms = node_selector_terms
                )
            )
        else:
            return simple_error_handle("不支持{}这种调度".format(node_affinity_type))
    elif action == "delete_node_affinity":
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
    return update_deployment_v2(deploy_name=deploy_name, namespace=namespace, action=action, image=image, replicas=replicas,toleration=toleration,node_affinity=node_affinity,\
                pod_anti_affinity=pod_anti_affinity,pod_affinity=pod_affinity,labels=labels)

def delete_deployment(namespace,deploy_name=None):
    api_response =  client.AppsV1Api().delete_namespaced_deployment(
        name=deploy_name,
        namespace=namespace,
        body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
    )
    # print("Deployment deleted. status='%s'\n" % str(api_response.status))
    status="{}".format(api_response.status)
    return jsonify({"update_status":status})

@k8s_deployment.route('/delete_deploy',methods=['POST'])  
def delete_deploy():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("delete_deploy接受到的数据:{}".format(data))
    namespace = data.get('namespace').strip()
    deploy_name = data.get('deploy_name').strip()
    return delete_deployment(deploy_name=deploy_name,namespace=namespace)

@k8s_deployment.route('/get_deployment_list', methods=('GET', 'POST'))
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
        if (i >= 0):
            # current_app.logger.debug(deployment)
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
            pod_affinity = None
            pod_anti_affinity = None

            template_spec = deployment.spec.template.spec
            affinity = template_spec.affinity

            if affinity:
                node_affinity = affinity.node_affinity
                pod_affinity = affinity.pod_affinity
                pod_anti_affinity = affinity.pod_anti_affinity
            if (name == "flask-tutorial"):
                # current_app.logger.debug(deployment)
                current_app.logger.debug(affinity)
                current_app.logger.debug(pod_anti_affinity)
            containers = template_spec.containers

            container_names = []
            container_images = []
            for container in containers:
                c_name = container.name
                c_image = container.image
                container_names.append(c_name)
                container_images.append(c_image)
            # containerInfo = {"name":container_names[0],"image":container_images[0]}
            # containerInfo = {"image": container_images[0]}
            image = container_images[0]
            node_selector = template_spec.node_selector
            tolerations = template_spec.tolerations

            status = deployment.status
            # ready = "{}/{}".format(status.ready_replicas,status.replicas)
            ready = "{}/{}".format(status.ready_replicas, replicas)
            available_replicas = status.available_replicas
            updated_replicas = status.updated_replicas
            
            info = {}
            info["replicas"] = replicas
            info["ready"] = ready
            info["available_replicas"] = available_replicas
            info["updated_replicas"] = updated_replicas
            info["labels"] = labels
            info["image"] = image
            info["node_selector"] = node_selector
            #构建deployment结构体
            my_deploy = {}
            my_deploy["name"] = name
            my_deploy["namespace"] = namespace
            my_deploy["info"] = info
            my_deploy["tolerations"] = tolerations
            my_deploy["affinity"] = affinity
            # my_deploy["node_affinity"] = node_affinity
            # my_deploy["pod_affinity"] = pod_affinity
            # my_deploy["pod_anti_affinity"] = pod_anti_affinity
            deployment_list.append(my_deploy)

        i = i + 1
    return json.dumps(deployment_list, indent=4, cls=MyEncoder)
    # return json.dumps(deployment_list,default=lambda obj: obj.__dict__,indent=4)

@k8s_deployment.route('/get_deployment_name_list',methods=('GET','POST'))
def get_deployment_name_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
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

def create_single_deployment_object(deployment):
    meta = deployment.metadata
    deployment_name = meta.name
    create_time = time_to_string(meta.creation_timestamp)
    cluster_name = meta.cluster_name
    labels = meta.labels
    namespace = meta.namespace

    spec = deployment.spec
    replicas = spec.replicas
    selector = spec.selector
    strategy = spec.strategy
    min_ready_seconds = spec.min_ready_seconds
    revision_history_limit = spec.revision_history_limit

    template = spec.template
    template_labels = template.metadata.labels
    node_affinity = None
    pod_affinity = None
    pod_anti_affinity = None

    template_spec = deployment.spec.template.spec
    tolerations = template_spec.tolerations
    affinity = template_spec.affinity

    if affinity:
        node_affinity = affinity.node_affinity
        pod_affinity = affinity.pod_affinity
        pod_anti_affinity = affinity.pod_anti_affinity
    containers = deployment.spec.template.spec.containers

    container_list = []
    for C in containers:
        name = C.name
        image = C.image
        mycontainer = {"name": name, "image": image}
        container_list.append(mycontainer)

    status = deployment.status
    ready_replicas = status.ready_replicas
    updated_replicas = status.updated_replicas
    available_replicas = status.available_replicas
    ready = "{}/{}".format(ready_replicas, replicas)
    mystatus = {}
    mystatus['replicas'] = replicas
    mystatus['ready'] = ready
    mystatus['available_replicas'] = available_replicas
    mystatus['up-to-date'] = updated_replicas

    mydeployment = {}
    mydeployment['name'] = deployment_name
    mydeployment['namespace'] = namespace
    mydeployment['labels'] = labels
    mydeployment['selector'] = selector
    mydeployment['create_time'] = create_time
    mydeployment['status'] = mystatus
    mydeployment['template_labels'] = template_labels
    mydeployment['strategy'] = strategy
    mydeployment['min_ready_seconds'] = min_ready_seconds
    mydeployment['revision_history_limit'] = revision_history_limit
    mydeployment['tolerations'] = tolerations
    mydeployment['node_affinity'] = node_affinity
    mydeployment['pod_affinity'] = pod_affinity
    mydeployment['pod_anti_affinity'] = pod_anti_affinity
    mydeployment['container_list'] = container_list
    return mydeployment

def create_single_hpa_object(hpa):
    meta = hpa.metadata
    name = meta.name
    namespace = meta.namespace
    create_time = time_to_string(meta.creation_timestamp)
    spec = hpa.spec
    maxReplicas = spec.max_replicas
    minReplicas = spec.min_replicas
    scaleTargetRef = spec.scale_target_ref
    targetCPUUtilizationPercentage = spec.target_cpu_utilization_percentage

    status = hpa.status
    currentCPUUtilizationPercentage = status.current_cpu_utilization_percentage
    current_replicas = status.current_replicas
    myhpa = {}
    myhpa["name"] = name
    myhpa["namespace"] = namespace
    myhpa['create_time'] = create_time
    myhpa["currentReplicas"] = current_replicas
    myhpa["minReplicas"] = minReplicas
    myhpa["maxReplicas"] = maxReplicas
    myhpa["scaleTargetRef"] = scaleTargetRef
    myhpa["targetCPUUtilizationPercentage"] = targetCPUUtilizationPercentage
    myhpa["currentCPUUtilizationPercentage"] = currentCPUUtilizationPercentage
    return myhpa

# @k8s_deployment.route('/get_hpa__by_deployment_name',methods=('GET','POST'))
def get_hpa_by_deployment_name(namespace,deploy_name):
    # data = json.loads(request.get_data().decode("utf-8"))
    # current_app.logger.debug("接收的数据:{}".format(data))
    # namespace = handle_input(data.get("namespace"))
    # deploy_name = handle_input(data.get("name"))
    myclient = client.AutoscalingV1Api()
    hpas = myclient.list_namespaced_horizontal_pod_autoscaler(namespace=namespace)
    hpa = None
    for item in hpas.items:
        scaleTargetRef = item.spec.scale_target_ref
        kind = scaleTargetRef.kind
        name = scaleTargetRef.name
        if kind=='Deployment' and name  == deploy_name:
            hpa = item
            break
    return hpa

@k8s_deployment.route('/get_deployment_detail', methods=('GET', 'POST'))
def get_deployment_detail():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("收到的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    deployment_name = handle_input(data.get('name'))
    myclient = client.AppsV1Api()
    field_selector = "metadata.name={}".format(deployment_name)
    # print(field_selector)

    deployments = myclient.list_namespaced_deployment(namespace=namespace, field_selector=field_selector)

    deployment = None
    for item in deployments.items:
        if item.metadata.name == deployment_name:
            deployment = item
            break
    if deployment == None:
        return simple_error_handle("找不到deployment相关信息")
    # 生成deployment的结构体
    mydeployment = create_single_deployment_object(deployment)
    # 获取hpa信息
    hpa = get_hpa_by_deployment_name(namespace,deployment_name)
    if hpa:
        myhpa = create_single_hpa_object(hpa)
        mydeployment['hpa'] = myhpa
    # 获取事件
    event_list = get_event_list_by_name(namespace=namespace, input_kind="Deployment", input_name=deployment_name)
    mydeployment["event_list"] = event_list
    return json.dumps(mydeployment,indent=4,cls=MyEncoder)
