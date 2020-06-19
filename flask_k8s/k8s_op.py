from flask import Flask,jsonify,Response,make_response,Blueprint,request
from kubernetes import client,config
from dateutil import tz, zoneinfo
import json,os
from datetime import datetime,date
import math
from .k8s_decode import DateEncoder
import requests
import time 
import pytz
import ssl
import yaml
import math
from kubernetes.client.rest import ApiException

k8s_op = Blueprint('k8s_op',__name__,url_prefix='/k8s_op')
dir_path = os.path.dirname(os.path.abspath(__file__))

def utc_to_local(utc_time_str, utc_format='%Y-%m-%dT%H:%M:%S.%fZ'):
    local_tz = pytz.timezone('Asia/Shanghai')
    local_format = "%Y-%m-%d %H:%M:%S"
    utc_dt = datetime.strptime(utc_time_str, utc_format)
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    time_str = local_dt.strftime(local_format)
    return time_str
    # return datetime.fromtimestamp(int(time.mktime(time.strptime(time_str, local_format))))
def str_to_int(str):    
    # return str=="" ? 1 : int(str)  
    return 1 if str=="" else int(str)
def str_to_float(str):    
    return 1 if str=="" else float(str)

@k8s_op.route('/create_deploy_by_yaml',methods=('GET','POST'))
def create_deploy_by_yaml():
    if request.method == "POST":
        data = request.get_data()
        json_data = json.loads(data.decode("utf-8"))
        yaml_name = json_data.get("yaml_name")
        if yaml_name == None or yaml_name == "":
            msg = "需要提供yaml文件" 
            return jsonify({"error":"1001","msg":msg})
        yaml_dir = os.path.join(dir_path,"yaml")
        file_path = os.path.join(yaml_dir,yaml_name)
        if not os.path.exists(file_path):
            msg = "找不到此文件{}".format(file_path)
            return jsonify({"error":"1001","msg":msg})
        
        with open(file_path,encoding='utf-8') as f:
            cfg = f.read()
            obj = yaml.safe_load(cfg)  # 用load方法转字典
            try:
                myclient = client.AppsV1Api()
                resp = myclient.create_namespaced_deployment(body=obj, namespace="default")
                # print(resp)
                print("Deployment created. name='%s' " % resp.metadata.name)
            except ApiException as e:
                return make_response(json.dumps({"error":"1001","msg":str(e)},indent=4, cls=DateEncoder),1001)

    return jsonify({"msg":"创建deployment成功"})

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
def get_deployment_by_name(namespace,deploy_name):
    deployments = client.AppsV1Api().list_namespaced_deployment(namespace=namespace)
    
    deployment = None
    for  deploy in deployments.items:
        if deploy.metadata.name == deploy_name:
            deployment = deploy
            break
    return deployment



           
def update_deployment(deploy_name,namespace,image=None,replicas=None):
    # '/apis/apps/v1/namespaces/{namespace}/deployments/{name}', 'PATCH'
    deployment = get_deployment_by_name(namespace,deploy_name)
    if (deployment == None):
        return jsonify({"error":"1003","msg":"找不到该deployment"})
    deployment.spec.template.spec.containers[0].image=image
    deployment.spec.replicas = replicas
    api_response =  client.AppsV1Api().patch_namespaced_deployment(
        name=deploy_name,
        namespace=namespace,
        body=deployment
    )
    # print("Deployment updated. status='%s'\n" % str(api_response.status))
    status="{}".format(api_response.status)
    return jsonify({"update_status":status})
@k8s_op.route('/create_deploy',methods=('GET','POST'))
def create_deploy():
    error = ""
    if request.method == "POST":
        data = request.get_data()
        json_data = json.loads(data.decode("utf-8"))
        project = json_data.get("project").strip()
        environment = json_data.get("environment").strip()
        cluster = json_data.get("cluster").strip()
        project = json_data.get("project").strip()
        
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
        # print(labels)
        myclient = client.AppsV1Api()
        deployment = create_deployment_object(name=imageName,namespace=namespace,image=image,port=containerPort,\
            image_pull_policy=imagePullPolicy,imagePullSecret=imagePullSecret ,labels=labels,replicas=replicas,cpu=cpu,memory=memory,\
            liveness_probe=liveness_probe,readiness_probe=readiness_probe)
        print(type(deployment))
        to_yaml = yaml.load(json.dumps(deployment,indent=4,cls=DateEncoder))
        file = os.path.join(dir_path,"demo-deployment.yaml")
        stream = open(file,'w')
        yaml.safe_dump(to_yaml,stream,default_flow_style=False)
        
        status = create_deployment(api_instance=myclient,namespace=namespace,deployment=deployment)
        
        # return jsonify({'status':'status'})
        return json.dumps(deployment,indent=4,cls=DateEncoder)
        
        # try:
        #     create_deployment(myclient, deployment)
        # except Exception as e:
        #     print('发生了异常:', e)
    return jsonify({'a':1})   

@k8s_op.route('/update_deploy',methods=('GET','POST'))  
def update_deploy():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("接受到的数据:{}".format(data))
    namespace = data.get('namespace').strip()
    deploy_name = data.get('deploy_name').strip()
    replicas = str_to_int(data.get('replicas').strip())
    project = data.get('project').strip()
    env = data.get('env').strip()
    imageRepo = data.get('imageRepo').strip()
    imageName = data.get('imageName').strip()
    imageTag = data.get('imageTag').strip()
    image = "{}/{}-{}/{}:{}".format(imageRepo,project,env,imageName,imageTag)
    print(image)
    return update_deployment(deploy_name=deploy_name,namespace=namespace,replicas=replicas,image=image)

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
            
	# 'spec': {
	# 	'hosts': ['flask-tutorial'],
	# 	'http': [{
	# 		'route': [{
	# 			'destination': {
	# 				'host': 'flask-tutorial',
	# 				'subset': 'prod'
	# 			},
	# 			'weight': 0
	# 		}, {
	# 			'destination': {
	# 				'host': 'flask-tutorial',
	# 				'subset': 'canary'
	# 			},
	# 			'weight': 100
	# 		}]
	# 	}]
	# } 
def update_virtual_service(vs_name,namespace,prod_weight,canary_weight):
    myclient = client.CustomObjectsApi()
    #先获取到对应的vs名称
    vs = get_vs_by_name(namespace,vs_name)
    if vs == None:
        return jsonify({"error":"1003","msg":"找不到该vs"})
    print(vs)
    #这样必须规定第一条route是生产版本，第二条是灰度版本
    print(vs['spec']['http'][0]['route'][0]['weight'])
    print(vs['spec']['http'][0]['route'][1]['weight'])
    vs['spec']['http'][0]['route'][0]['weight'] = prod_weight
    vs['spec']['http'][0]['route'][1]['weight'] = canary_weight
    api_response = myclient.patch_namespaced_custom_object( group="networking.istio.io",
                                                            version="v1alpha3",
                                                            plural="virtualservices",
                                                            name=vs_name,
                                                            namespace=namespace,
                                                            body=vs)
    # deployment.spec.template.spec.containers[0].image=image
    # deployment.spec.replicas = replicas
    # api_response =  client.AppsV1Api().patch_namespaced_deployment(
    #     name=deploy_name,
    #     namespace=namespace,
    #     body=deployment
    # )
    # # print("Deployment updated. status='%s'\n" % str(api_response.status))
    # {'hosts': ['flask-tutorial'], 'http': [{'route': [{'destination': {'host': 'flask-tutorial', 'subset': 'prod'}, 'weight': 80}, {'destination': {'host': 'flask-tutorial', 'subset': 'canary'}, 'weight': 20}]}]}
    print(api_response['spec'])
    status="{}".format(api_response['spec']['http'])
    
    return jsonify({"update_status":status})

@k8s_op.route('/update_vs',methods=('GET','POST'))
def update_vs():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("接受到的数据:{}".format(data))
    namespace = data.get('namespace').strip()
    vs_name = data.get('vs_name').strip()
    canary_weight = math.ceil( str_to_int(data.get('canary_weight').strip()))
    if(canary_weight < 0 or canary_weight > 100):
        return jsonify({"error":1003,"msg":"灰度值需在1-100之间"})
    prod_weight = 100 - canary_weight
    return update_virtual_service(vs_name=vs_name,namespace=namespace,prod_weight=prod_weight,canary_weight=canary_weight)