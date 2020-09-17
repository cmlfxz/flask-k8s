from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from flask_k8s.k8s_decode import MyEncoder
from flask_k8s.util import *
from kubernetes import client,config
from kubernetes.client.rest import ApiException
from .cluster import get_event_list_by_name

from flask_k8s.k8s import k8s


#新增根据名字获取pod内存使用情况
def get_pod_usage_by_name(namespace,name):
    current_app.logger.debug(namespace+" "+name)
    myclient = client.CustomObjectsApi()
    if namespace == "" or namespace=='all':
        return "需要具体的namespace"
    # / apis / {group} / {version} / namespaces / {namespace} / {plural}
    # /apis/metrics.k8s.io/v1beta1/namespaces/ms-dev/pods
    pods = myclient.list_namespaced_custom_object(namespace=namespace,
                                                  group="metrics.k8s.io",
                                                  version="v1beta1",
                                                  plural="pods",
                                                  timeout_seconds=5)
    pod_usage = {}
    if len(pods['items']) > 0:
        for pod in pods['items']:
            if pod['metadata']['name'] == name:
                containers =  pod['containers']
                container_list = []

                cpu_all = 0
                memory_all = 0
                pod_cpu_usage = 0
                pod_memory_usage = 0
                j = 0
                for container in containers:
                    container_name = container['name']
                    cpu = handle_cpu(container['usage']['cpu'] )
                    container_cpu_usage = "{}m".format(cpu)
                    memory = handle_memory(container['usage']['memory'])
                    container_memory_usage = "{}Mi".format(memory)
                    container_usage = {"name":container_name,"cpu":container_cpu_usage,"memory":container_memory_usage}
                    container_list.append(container_usage)

                    #汇总容器数据
                    cpu_all = cpu_all + cpu
                    memory_all = memory_all + memory
                    # pod_cpu_usage =  "{}m".format(cpu_all)
                    # pod_memory_usage = "{}Mi".format(memory_all)
                    j = j + 1
                pod_usage['name'] = name
                pod_usage["pod_cpu_usage"] = cpu_all
                pod_usage["pod_memory_usage"] = memory_all
                pod_usage["container_list"] = container_list
                # current_app.logger.debug("整个pod的使用情况:{}".format(pod_usage))
                break
    return pod_usage


#pod详情页
@k8s.route('/get_pod_detail', methods=('GET', 'POST'))
def get_pod_detail():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("收到的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    pod_name = handle_input(data.get('name'))
    myclient = client.CoreV1Api()
    field_selector = "metadata.name={}".format(pod_name)
    print(field_selector)
    pods = myclient.list_namespaced_pod(namespace=namespace, field_selector=field_selector)

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
    volume_list = []
    for v in volumes:
        print(v)
        volume = None
        if v.empty_dir is not None:
            volume = {"name":v.name,"empty_dir":v.empty_dir}
        elif v.nfs is not  None:
            volume = {"name":v.name,"nfs":v.nfs}
        elif v.config_map is not  None:
            volume= {"name":v.name,"config_map":v.config_map}
        # elif v.downward_api is not  None:
        #     volume = {"name":v.name,"downward_api":""}
        #     volume = {"name":v.name,"downward_api":v.downward_api}
        elif v.flex_volume is not  None:
            volume = {"name":v.name,"flex_volume":v.flex_volume}
        elif v.host_path is not  None:
            volume = {"name":v.name,"host_path":v.host_path}
        elif v.persistent_volume_claim is not  None:
            volume = {"name":v.name,"persistent_volume_claim":v.persistent_volume_claim}
        elif v.rbd is not  None:
            volume = {"name":v.name,"rbd":v.rbd}
        elif v.secret is not  None:
            volume = {"name":v.name,"secret":v.secret}
        # elif v.cephfs is not  None:
        #     volume = {"name":v.name,"cephfs":v.cephfs}
        # elif v.aws_elastic_block_store is not  None:
        #     volume = {"name":v.name,"aws_elastic_block_store":v.aws_elastic_block_store}
        else:
            volume = {"name":v.name}
        volume_list.append(volume)
    # print(volume_list)
    containers = spec.containers
    init_containers = spec.init_containers

    status = pod.status
    phase = status.phase
    host_ip = status.host_ip
    pod_ip = status.pod_ip
    # 获取pod事件
    event_list = get_event_list_by_name(namespace=namespace,input_kind="Pod",input_name=name)
    mypod = {}
    mypod = {
        "name": name,
        "namespace": namespace,
        "node": host_ip,
        "pod_ip": pod_ip,
        "pod_labels": pod_labels,
        "status": phase,
        "create_time": create_time,
        # spec关键信息
        "affinity": affinity,
        "nodeAffinity": node_affinity,
        "podAffinity": pod_affinity,
        "podAntiAffinity": pod_anti_affinity,
        "hostNetwork": host_network,
        "imagePullSecrets": image_pull_secrets,
        "nodeSelector": node_selector,
        "restartPolicy": restart_policy,
        "serviceAccountName": service_account_name,
        # "terminationGracePeriodSeconds":terminationGracePeriodSeconds,
        "tolerations": tolerations,
        "volumes": volume_list,
        # 容器信息
        "containers": containers,
        # 初始化容器
        "initContainers": init_containers,
    }
    mypod["event_list"] = event_list
    # return json.dumps(pod,default=lambda obj: obj.__dict__,indent=4)
    # return jsonify(pod)
    return json.dumps(mypod, indent=4, cls=MyEncoder)

#弃用 demo dashboard在用
@k8s.route('/get_pod_list', methods=('GET', 'POST'))
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
        if (i >= 0):
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
            container_info = ""
            args = command = ""
            env = ""
            liveness_probe = readiness_probe = ""
            resources = ""
            volume_mounts = ""
            ports = ""
            i = 0
            for c in containers:
                if (i == 0):
                    container_name = c.name
                    args = c.args
                    command = c.command
                    env = c.env
                    image = c.image
                    image_pull_policy = c.image_pull_policy
                    liveness_probe = c.liveness_probe
                    readiness_probe = c.readiness_probe
                    resources = c.resources
                    volume_mounts = c.volume_mounts
                    ports = c.ports
                    container_info = {"container_name": container_name, "image": image,
                                      "image_pull_policy": image_pull_policy, "ports": ports}

                i = i + 1
            status = pod.status
            phase = status.phase
            host_ip = status.host_ip
            pod_ip = status.pod_ip

            pod_info = {"create_time": create_time, "namespace": namespace, "pod_ip": pod_ip, "node": host_ip,
                        "status": phase, "affinity": affinity}
            others = {"image_pull_secrets": image_pull_secrets, "restart_policy": restart_policy,
                      "node_selector": node_selector, \
                      "service_account_name": service_account_name, "host_network": host_network}

            mypod = {"name": name, "pod_info": pod_info, \
                     "others": others, "container_info": container_info, \
                     "readiness_probe": readiness_probe, "resources": resources, "volume_mounts": volume_mounts, \
                     "env": env
                     }

            pod_list.append(mypod)
        i = i + 1
    # return json.dumps(pod_list,default=lambda obj: obj.__dict__,indent=4)
    return json.dumps(pod_list, indent=4, cls=MyEncoder)

#根据命名空间获取pod列表 做一个聚合操作,把内存使用量也聚合进来
@k8s.route('/get_namespaced_pod_list', methods=('GET', 'POST'))
def get_namespaced_pod_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all":
        pods = myclient.list_pod_for_all_namespaces(watch=False)
    else:
        pods = myclient.list_namespaced_pod(namespace=namespace, watch=False)
    i = 0
    pod_list = []
    for pod in pods.items:
        if (i >= 0):
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
                if (i == 0):
                    container_name = c.name
                    image = c.image
                i = i + 1
            status = pod.status
            phase = status.phase
            node = spec.node_name
            pod_ip = status.pod_ip
            restart_count = None
            if status.container_statuses:
                restart_count = status.container_statuses[0].restart_count
            mypod = {"name": name, "namespace": namespace, "node": node, "pod_ip": pod_ip, "status": phase,
                     "image": image, "restart_count": restart_count}
            # 以下4行修复rancher有些pod获取不到性能数据
            mypod['cpu_usage(m)'] = 0
            mypod['memory_usage(M)'] = 0
            mypod['container_usage'] = []
            try:
                pod_usage = get_pod_usage_by_name(namespace,name)
                # 根据pod命名空间，内存获取pod的内存，CPU
                mypod['cpu_usage(m)'] = pod_usage['pod_cpu_usage']
                mypod['memory_usage(M)'] = pod_usage['pod_memory_usage']
                mypod['container_usage'] = pod_usage['container_list']
            except Exception as e:
                current_app.logger.debug("获取pod性能数据出错")

            mypod["create_time"]=create_time
            # current_app.logger.debug("pod详情:{}".format(mypod))
            pod_list.append(mypod)
        i = i + 1
    return json.dumps(pod_list, indent=4, cls=MyEncoder)

# 根据节点获取pod列表
@k8s.route('/get_pod_list_by_node', methods=('GET', 'POST'))
def get_pod_list_by_node():
    data = json.loads(request.get_data().decode("utf-8"))
    # namespace = data.get("namespace").strip()
    node = handle_input(data.get('node'))
    if not node:
        return simple_error_handle("必须要node参数")
    myclient = client.CoreV1Api()
    # 在客户端筛选属于某个node的pod
    pods = myclient.list_pod_for_all_namespaces(watch=False)

    pod_list = []
    mypod = {}
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
                if (i == 0):
                    container_name = c.name
                    image = c.image
                i = i + 1
            status = pod.status
            phase = status.phase
            # host_ip = status.host_ip
            node = spec.node_name
            pod_ip = status.pod_ip
            restart_count = None
            if isinstance(status.container_statuses,list):
                restart_count = status.container_statuses[0].restart_count
            mypod = {"name": name, "namespace": namespace, "node": node, "pod_ip": pod_ip, "status": phase,
                     "image": image, "restart_count": restart_count}
            # 以下4行修复rancher有些pod获取不到性能数据
            mypod['cpu_usage(m)'] = 0
            mypod['memory_usage(M)'] = 0
            # mypod['pod_performance'] = pod_performance
            mypod['container_usage'] = []
            try:
                pod_usage = get_pod_usage_by_name(namespace,name)
                # 根据pod命名空间，内存获取pod的内存，CPU
                # pod_performance = "{}/{}".format(pod_usage['pod_cpu_usage'],pod_usage['pod_memory_usage'])
                mypod['cpu_usage(m)'] = pod_usage['pod_cpu_usage']
                mypod['memory_usage(M)'] = pod_usage['pod_memory_usage']
                # mypod['pod_performance'] = pod_performance
                mypod['container_usage'] = pod_usage['container_list']
            except Exception as e:
                current_app.logger.debug("获取pod性能数据出错")

            mypod["create_time"] = create_time
            pod_list.append(mypod)
    return json.dumps(pod_list, indent=4, cls=MyEncoder)


@k8s.route('/delete_pod', methods=('GET', 'POST'))
def delete_pod():
    data = json.loads(request.get_data().decode('UTF-8'))
    current_app.logger.debug("接受到的数据:{}".format(data))
    namespace = handle_input(data.get('namespace'))
    pod_name = handle_input(data.get('name'))

    try:
        api_response =  client.CoreV1Api().delete_namespaced_pod(
            name=pod_name,
            namespace=namespace,
            body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        )
    except ApiException as e:
        if isinstance(e.body, dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            message = e.body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        current_app.logger.debug(msg)
        return jsonify({'error': '删除失败', "msg": msg})
    return jsonify({"ok":"删除成功"})
