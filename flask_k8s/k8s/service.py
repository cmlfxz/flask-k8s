from flask import Flask,jsonify,Blueprint,request,current_app
from flask_cors import *
from flask_k8s.k8s_decode import MyEncoder
from flask_k8s.util import *
from .cluster import get_event_list_by_name

from kubernetes import client,config
from kubernetes.client.rest import ApiException

# from kubernetes.client.models.v1_namespace import V1Namespace

# 导入蓝图
from flask_k8s.k8s import k8s


@k8s.route('/get_service_list',methods=('GET','POST'))
def get_service_list():
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

@k8s.route('/delete_service', methods=('GET', 'POST'))
def delete_service():
    # myclient = client.CoreV1Api()
    # myclient.delete_namespaced_service(name=service_name,namespace=namespace)
    
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace  = handle_input(data.get('namespace'))
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.CoreV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_service(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})
    
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

@k8s.route('/delete_ingress', methods=('GET', 'POST'))
def delete_ingress():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.ExtensionsV1beta1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_ingress(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})
