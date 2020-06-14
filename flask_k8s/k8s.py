"""
Reads the list of available API versions and prints them. Similar to running
`kubectl api-versions`.
"""
from flask import Flask,jsonify,Response,make_response,Blueprint
from kubernetes import client,config
from dateutil import tz, zoneinfo
import json,os
from datetime import datetime,date
import math
from .k8s_decode import DateEncoder
import requests

k8s = Blueprint('k8s',__name__,url_prefix='/k8s')
# app = Flask(__name__)
def takename(e):
    return e['name']
# dir_path = os.path.dirname(os.path.abspath(__file__))
#参数是datetime
def time_to_string(dt):
    tz_sh = tz.gettz('Asia/Shanghai')
    return  dt.astimezone(tz_sh).strftime("%Y-%m-%d %H:%M:%S") 




#列出gateway
@k8s.route('/get_gateway_list')
def get_gateway_list():
    myclient = client.CustomObjectsApi()
    obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="gateways")
    # print(type(gateways))
    # print(gateways)

    gateways = obj['items']
    # print(type(gateways))
    gateway_list = []
    i = 0
    for gateway in gateways:
        if(i>=0):
            # print(type(gateway))
            # print(gateway)
            meta = gateway['metadata'] 
            spec = gateway['spec']
            # print(type(meta))
            # print(spec)
            name = meta['name']
            namespace = meta['namespace']
            # create_time = time_to_string(meta['creationTimestamp'])
            create_time = meta['creationTimestamp']
            selector = spec['selector']
            servers = spec['servers']
            
            domain_list = []
            
            for server in servers:
                domain = server['hosts']
                domain_list.append(domain)
            
            mygateway = {"name":name,"namespace":namespace,"selector":selector,"servers":servers,"domain_list":domain_list,"create_time":create_time,}
            gateway_list.append(mygateway)
        i = i + 1
    return json.dumps(gateway_list,indent=4,cls=DateEncoder)
    # return jsonify({"a":1})


#列出vs
@k8s.route('/get_virtual_service_list')
def get_virtual_service_list():

    myclient = client.CustomObjectsApi()
    obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="virtualservices")
    virtual_services = obj['items']
    # print(type(virtual_services))
    virtual_service_list = []
    i = 0
    for virtual_service in virtual_services:
        if(i>=0):
            # print(type(virtual_service))
            # print(virtual_service)
            meta = virtual_service['metadata'] 
            spec = virtual_service['spec']
            # print(type(meta))
            # print(spec)
            name = meta['name']
            namespace = meta['namespace']
            # create_time = time_to_string(meta['creationTimestamp'])
            create_time = meta['creationTimestamp']
            try:
                gateways = spec['gateways']
            except Exception as e: 
                gateways = None
                print(e)
            hosts = spec['hosts']
            http = spec['http']
            myvirtual_service = {"name":name,"namespace":namespace,"gateways":gateways,"hosts":hosts,"http":http,"create_time":create_time,}
            virtual_service_list.append(myvirtual_service)
            
        i = i + 1
    return json.dumps(virtual_service_list,indent=4,cls=DateEncoder)
    # return jsonify({"a":1})

#列出vs
@k8s.route('/get_destination_rule_list')
def get_destination_rule_list():
    myclient = client.CustomObjectsApi()
    obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="destinationrules")
    #obj是一个字典
    destination_rules = obj['items']
    # print(type(destination_rules))
    destination_rule_list = []
    i = 0
    for destination_rule in destination_rules:
        if(i>=0):
            # print(type(destination_rule))
            print(destination_rule)
            meta = destination_rule['metadata'] 
            spec = destination_rule['spec']
            # print(type(meta))
            # print(spec)
            name = meta['name']
            namespace = meta['namespace']
            # create_time = time_to_string(meta['creationTimestamp'])
            create_time = meta['creationTimestamp']

            host = spec['host']
            subsets = spec['subsets']
            mydestination_rule = {"name":name,"namespace":namespace,"host":host,"subsets":subsets,"create_time":create_time,}
            destination_rule_list.append(mydestination_rule)
            
        i = i + 1
    return json.dumps(destination_rule_list,indent=4,cls=DateEncoder)
    # return jsonify({"a":1})

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
@k8s.route('/get_namespace_list')
def get_namespace_list():
    myclient = client.CoreV1Api()
    namespace_list = []
    for ns in myclient.list_namespace().items:
        meta = ns.metadata
        create_time = time_to_string(meta.creation_timestamp)
        namespace= {"名字":meta.name,"集群":meta.cluster_name,"创建时间":create_time,"标签":meta.labels}
        namespace_list.append(namespace)
    # return jsonify(namespace_list)
    return json.dumps(namespace_list,default=lambda obj: obj.__dict__,sort_keys=True,indent=4)


@k8s.route('/get_service_list')
def get_service_list():
    myclient = client.CoreV1Api()
    # services = myclient.list_service_for_all_namespaces(watch=False)
    #/api/v1/namespaces/{namespace}/services
    services = myclient.list_namespaced_service(namespace='ms-prod')
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

        service = {"name":name,"create_time":create_time,"namespace":namespace,\
            "labels":labels,"cluster_ip":cluster_ip,"policy":policy,\
            "load_balancer_ip":load_balancer_ip,"ports":ports,"selector":selector,"service_type":service_type,"status":status}
        service_list.append(service)
    
    # return json.dumps(service_list,default=lambda obj: obj.__dict__,sort_keys=True,indent=4)
    return json.dumps(service_list,indent=4,cls=DateEncoder)

# from flask_k8s.util import *
@k8s.route('/get_pod_list')
def get_pod_list():
    myclient = client.CoreV1Api()
    # pods = myclient.list_pod_for_all_namespaces(watch=False)
    pods = myclient.list_namespaced_pod('ms-prod')
    i = 0
    pod_list = []
    for pod in pods.items:
        if (i ==0):
            print(pod)
            meta = pod.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name

            labels = meta.labels
            namespace = meta.namespace 
            
            spec = pod.spec
            affinity = spec.affinity
            host_network = spec.host_network
            image_pull_secrets = spec.image_pull_secrets[0]
            node_selector = spec.node_selector
            restart_policy = spec.restart_policy
            security_context = spec.security_context
            service_account_name = spec.service_account_name
            tolerations = spec.tolerations
            
            containers = spec.containers
            container_list = []
            for c in containers: 
                cname = c.name
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
                
                container = {"name":cname,"image":image,"image_pull_policy":image_pull_policy, "resources":resources,"ports":ports,"liveness_probe":liveness_probe,\
                    "readiness_probe":readiness_probe,"env":env,"volume_mounts":volume_mounts}
                container_list.append(container)
            
            status = pod.status
            phase = status.phase 
            host_ip = status.host_ip
            pod_ip = status.pod_ip
            
            mypod = {"name":name,"pod_ip":pod_ip,"labels":labels,"namespace":namespace,"affinity":affinity,"host_network":host_network,"image_pull_secrets":image_pull_secrets,\
                "node_selector":node_selector,"restart_policy":restart_policy,"security_context":security_context,"container_list":container_list,"phase":phase,"host_ip":host_ip,\
                "create_time":create_time}

            pod_list.append(mypod)
        i = i + 1
    # jsonUtil=JsonUtil()  
    # retstr=jsonUtil.parseJsonObj(pod_list)
    return json.dumps(pod_list,indent=4,cls=DateEncoder)
    # return json.dumps(pod_list,default=lambda obj: obj.__dict__,indent=4)


@k8s.route('/get_deployment_list')
def get_deployment_list():
    myclient = client.AppsV1Api()
    deployments = myclient.list_namespaced_deployment("ms-prod")
    i = 0
    
    deployment_list = []
    for deployment in deployments.items:
        if (i>=0):
            # print(deployment)
            meta = deployment.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            print(labels)
            namespace = meta.namespace 
            
            spec = deployment.spec
            replicas = spec.replicas
            selector = spec.selector
            
            strategy = spec.strategy
            # print(strategy)
            template = spec.template
            template_labels = template.metadata.labels
            # print(template_labels)
            
            template_spec = template.spec 
            affinity = template_spec.affinity
            containers = template_spec.containers
            # env = containers.env
            image_pull_secrets = template_spec.image_pull_secrets[0]
            host_network = template_spec.host_network
            node_selector = template_spec.node_selector
            
            service_account_name = template_spec.service_account_name
            tolerations = template_spec.tolerations
            
            status = deployment.status
            mystatus = {"replicas":status.replicas,"available_replicas":status.available_replicas,\
                "unavailable_replicas":status.unavailable_replicas,"ready_replicas":status.ready_replicas}
            
            mydeployment = {"name":name,"namespace":namespace,"status":mystatus,"labels":labels,"replicas":replicas,"labels":template_labels,"containers":containers,\
                "affinity":affinity,"tolerations":tolerations,"node_selector":node_selector,"host_network":host_network,"strategy":strategy,"image_pull_secrets":image_pull_secrets,\
                "service_account_name":service_account_name,"create_time":create_time}
            
            deployment_list.append(mydeployment)
            
        i = i +1       
    return json.dumps(deployment_list,indent=4,cls=DateEncoder)
    # return json.dumps(deployment_list,default=lambda obj: obj.__dict__,indent=4)


@k8s.route('/get_daemonset_list')
def get_daemonset_list():
    myclient = client.AppsV1Api()
    daemonsets = myclient.list_daemon_set_for_all_namespaces()
    i = 0
    
    daemonset_list = []
    for daemonset in daemonsets.items:
        if (i==0):
            print(daemonset)
            meta = daemonset.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            print(labels)
            namespace = meta.namespace      
            spec = daemonset.spec
            template = spec.template
            template_spec = template.spec 
            affinity = template_spec.affinity
            containers = template_spec.containers
            container_list = []
            for container in containers:
                image = container.image
                volume_mounts = container.volume_mounts
                env = container.env
                mycontainer = {"image":image,"volume_mounts":volume_mounts,"env":env}
                container_list.append(mycontainer)
            host_network = template_spec.host_network
            node_selector = template_spec.node_selector
            
            tolerations = template_spec.tolerations
            
            status = daemonset.status
            mystatus = {"current_number_scheduled":status.current_number_scheduled,"desired_number_scheduled":status.desired_number_scheduled,\
                "number_available":status.number_available,"number_ready":status.number_ready,"number_unavailable":status.number_unavailable}
            
            mydaemonset = {"name":name,"create_time":create_time,"namespace":namespace,"labels":labels,"affinity":affinity,"containers":container_list,\
                "host_network":host_network,"tolerations":tolerations,"status":mystatus}
            daemonset_list.append(mydaemonset)
            
        i = i +1       
    return json.dumps(daemonset_list,indent=4,cls=DateEncoder)

        
@k8s.route('/get_node_list')
def get_node_list():
    myclient = client.CoreV1Api()
    nodes = myclient.list_node()
    
    i = 0
    
    node_list = []
    for node in nodes.items:
        if (i>=0):
            # print(node.spec)
            meta = node.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            # namespace = meta.namespace 
            
            spec = node.spec
            pod_cidr = spec.pod_cidr
            taints = spec.taints
            unschedulable = spec.unschedulable
            
            status = node.status
            address = status.addresses[0].address 
            
            capacity = status.capacity
            cpu_num = capacity['cpu']
            disk_space = math.ceil(int(capacity['ephemeral-storage'].split('Ki')[0])/1024/1024)
            memory =  math.ceil(int(capacity['memory'].split('Ki')[0])/1024/1024)
            pods = capacity['pods']
            
            mycapacity = {"cpu":cpu_num,"storage(G)":disk_space,"memory(G)":memory,"pods":pods}
            images_num = len(status.images)-1 
            node_info = status.node_info
            phase = status.phase
            
            mynode = {"name":name,"create_time":create_time,"cluster_name":cluster_name,"labels":labels,"pod_cidr":pod_cidr,"taints":taints,\
                "unschedulable":unschedulable,"address":address,"capacity":mycapacity,"images_num":images_num,"node_info":node_info,"phase":phase}
            
            print(mynode)
            node_list.append(mynode)
        i = i + 1
    return json.dumps(node_list,indent=4,cls=DateEncoder)
    # return jsonify({'a':1})

#列出namespace
@k8s.route('/get_configmap_list')
def get_configmap_list():
    myclient = client.CoreV1Api()
    # myclient = client.AppsV1Api()
    configmaps = myclient.list_namespaced_config_map(namespace="ms-prod")
    # configmaps = myclient.list_config_map_for_all_namespaces()
    configmap_list = []
    i = 0 
    for configmap in configmaps.items:
        if (i >=0):
            print(configmap)
            meta = configmap.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            print(labels)
            namespace = meta.namespace 
            data = configmap.data    
            
            myconfigmap = {"name":name,"create_time":create_time,"labels":labels,"namespace":namespace,"data":data}    
            configmap_list.append(myconfigmap) 
        i = i +1
    return json.dumps(configmap_list,indent=4,cls=DateEncoder)
    # return jsonify({'a':1})
        
#列出namespace
@k8s.route('/get_secret_list')
def get_secret_list():
    myclient = client.CoreV1Api()
    secrets = myclient.list_namespaced_secret("ms-prod")
    secret_list = []
    i = 0 
    for secret in secrets.items:
        if (i >=0):
            # print(secret)
            meta = secret.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            # print(labels)
            namespace = meta.namespace 
            data = secret.data    
            
            mysecret = {"name":name,"create_time":create_time,"cluster_name":cluster_name,"namespace":namespace,"data":data}    
            secret_list.append(mysecret) 
        i = i +1
    return json.dumps(secret_list,indent=4,cls=DateEncoder)

#列出job
@k8s.route('/get_job_list')
def get_job_list():
    myclient = client.BatchV1Api()
    jobs = myclient.list_job_for_all_namespaces()
    job_list = []
    i = 0 
    for job in jobs.items:
        if (i >=0):
            # print(job)
            meta = job.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            # print(labels)
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
    return json.dumps(job_list,indent=4,cls=DateEncoder)


#列出job
@k8s.route('/get_cronjob_list')
def get_cronjob_list():
    myclient = client.BatchV1beta1Api()
    cronjobs = myclient.list_cron_job_for_all_namespaces()
    cronjob_list = []
    i = 0 
    for cronjob in cronjobs.items:
        if (i >=0):
            print(cronjob)
            meta = cronjob.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            # print(labels)
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
    return json.dumps(cronjob_list,indent=4,cls=DateEncoder)

#列出storageclass
@k8s.route('/get_storageclass_list')
def get_storageclass_list():
    myclient = client.StorageV1Api()
    storageclasss = myclient.list_storage_class()
    storageclass_list = []
    i = 0 
    for storageclass in storageclasss.items:
        if (i == 0):
            # print(storageclass)
            meta = storageclass.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            annotations = meta.annotations
            mount_options = storageclass.mount_options
            parameters = storageclass.parameters
            provisioner = storageclass.provisioner
            reclaim_policy = storageclass.reclaim_policy
            # volume_binding_mode = storageclass.volume_binding_mode
            mystorageclass = {"name":name,"create_time":create_time,"provisioner":provisioner,\
                "mount_options":mount_options,"parameters":parameters,"reclaim_policy":reclaim_policy}    
            storageclass_list.append(mystorageclass) 
        i = i +1
    return json.dumps(storageclass_list,indent=4,cls=DateEncoder)

#列出pv
@k8s.route('/get_pv_list')
def get_pv_list():
    myclient = client.CoreV1Api()
    pvs = myclient.list_persistent_volume()
    pv_list = []
    i = 0 
    for pv in pvs.items:
        if (i >= 0):
            print(pv)
            meta = pv.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
 
            spec = pv.spec
            
            access_modes = spec.access_modes[0]
            capacity = spec.capacity['storage']
            nfs = spec.nfs
            pv_reclaim_policy = spec.persistent_volume_reclaim_policy
            storage_class_name = spec.storage_class_name
            volume_mode = spec.volume_mode
            claim_ref = spec.claim_ref

            status = pv.status.phase

            # volume_binding_mode = pv.volume_binding_mode
            mypv = {"name":name,"create_time":create_time,"status":status,"access_modes":access_modes,"capacity":capacity,"nfs":nfs,"pv_reclaim_policy":pv_reclaim_policy,\
                    "storage_class_name":storage_class_name,"volume_mode":volume_mode,"claim_ref":claim_ref}   

            pv_list.append(mypv) 
        i = i +1
    return json.dumps(pv_list,indent=4,cls=DateEncoder)

#列出pvc
@k8s.route('/get_pvc_list')
def get_pvc_list():
    myclient = client.CoreV1Api()
    pvcs = myclient.list_persistent_volume_claim_for_all_namespaces()
    pvc_list = []
    i = 0 
    for pvc in pvcs.items:
        if (i >= 0):
            print(pvc)
            meta = pvc.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            namespace = meta.namespace
 
            spec = pvc.spec
            
            access_modes = spec.access_modes[0]
            resources = spec.resources
            storage_class_name = spec.storage_class_name
            volume_name = spec.volume_name

            # status = pvc.status
            phase = pvc.status.phase
            # volume_binding_mode = pvc.volume_binding_mode
            mypvc = {"name":name,"volume_name":volume_name,"namespace":namespace,"create_time":create_time,"status":phase,"access_modes":access_modes,"resources":resources,\
                    "storage_class_name":storage_class_name}   

            pvc_list.append(mypvc) 
        i = i +1
    return json.dumps(pvc_list,indent=4,cls=DateEncoder)

@k8s.route('/get_statefulset_list')
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
            # labels = format_dict(meta.labels)
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
    return json.dumps(statefulset_list,indent=4,cls=DateEncoder)


#列出ingress
@k8s.route('/get_ingress_list')
def get_ingress_list():
    myclient = client.ExtensionsV1beta1Api()
    # /apis/extensions/v1beta1/namespaces/{namespace}/ingresses
    # myclient.list_namespaced_ingress()
    ingresss = myclient.list_ingress_for_all_namespaces()
    ingress_list = []
    i = 0 
    for ingress in ingresss.items:
        if (i >=0):
            print(ingress)
            meta = ingress.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            # print(labels)
            namespace = meta.namespace 
            
            spec = ingress.spec
            rules = spec.rules
            domain_list = []
            for rule in rules:
                domain = rule.host
                domain_list.append(domain)
            
            tls = spec.tls
            
            myingress = {"name":name,"create_time":create_time,"cluster_name":cluster_name,"namespace":namespace,\
                "domain_list":domain_list,"rule":rule,"tls":tls}    
            ingress_list.append(myingress) 
        i = i +1
    return json.dumps(ingress_list,indent=4,cls=DateEncoder)
