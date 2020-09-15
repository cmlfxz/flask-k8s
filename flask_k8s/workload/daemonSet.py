from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from flask_k8s.k8s_decode import MyEncoder
from flask_k8s.util import *
from kubernetes import client,config
from kubernetes.client.rest import ApiException
# from kubernetes.client.models.v1_namespace import V1Namespace

# 导入蓝图
from flask_k8s.workload import workload

@workload.route('/get_daemonset_list',methods=('GET','POST'))
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
            # print(daemonset)
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

@workload.route('/delete_daemonset',methods=('GET','POST'))
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