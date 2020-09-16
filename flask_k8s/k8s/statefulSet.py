from flask import Flask,jsonify,Blueprint,request,current_app
from flask_cors import *
from flask_k8s.k8s_decode import MyEncoder
from flask_k8s.util import *
from .cluster import get_event_list_by_name

from kubernetes import client,config
from kubernetes.client.rest import ApiException

# 导入蓝图
from flask_k8s.k8s import k8s


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


@k8s.route('/delete_statefulset',methods=('GET','POST'))
def delete_statefulset():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("k8s接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))
    
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.AppsV1Api()
    # myclient = client.AppsV1beta1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_stateful_set(namespace=namespace,name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除statefulset异常',"msg":msg})
    return jsonify({"ok":"删除成功"})