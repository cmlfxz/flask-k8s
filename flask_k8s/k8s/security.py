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


@k8s.route('/get_network_policy_list',methods=('GET','POST'))
def get_network_policy_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("policy接收的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.NetworkingV1Api()
    if namespace == "" or namespace == "all":
        policys = myclient.list_network_policy_for_all_namespaces()
    else:
        policys =myclient.list_namespaced_network_policy(namespace=namespace)
    i = 0
    policy_list = []
    for policy in policys.items:
        if (i >= 0):
            # print(policy)
            meta = policy.metadata
            create_time = time_to_string(meta.creation_timestamp)
            name = meta.name
            namespace = meta.namespace
            labels = meta.labels

            spec = policy.spec

            pod_selector = spec.pod_selector
            policy_types = spec.policy_types
            egress = spec.egress
            ingress = spec.ingress
            combine_policy = {}
            if ingress != None:
                combine_policy["ingress"] = ingress
            if egress != None:
                combine_policy["egress"] = egress
            my_policy = {}
            my_policy["name"] = name
            my_policy["namespace"] =namespace
            my_policy["labels"] = labels
            # my_policy["egress"] = egress
            # my_policy["ingress"] =ingress
            my_policy["policy_types"] = policy_types
            # 源(egress) / 目标(ingress)Pod
            my_policy["pod_selector"] =pod_selector
            my_policy["combine_policy"] = combine_policy
            my_policy["create_time"] =create_time
            policy_list.append(my_policy)
            # print(policy_list)
        i= i+1
    return json.dumps(policy_list,indent=4,cls=MyEncoder)
    # return jsonify({"ok":"get policy list"})

@k8s.route('/delete_network_policy', methods=('GET', 'POST'))
def delete_network_policy():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))
    namespace = handle_input(data.get("namespace"))

    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.NetworkingV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_network_policy(namespace=namespace, name=name)
    except ApiException as e:
        body = json.loads(e.body)
        msg = {"status": e.status, "reason": e.reason, "message": body['message']}
        return jsonify({'error': 'network_policy', "msg": msg})
    return jsonify({"ok": "删除成功"})

# http://192.168.11.51:1900/apis/security.istio.io/v1beta1/authorizationpolicies
@k8s.route('/get_istio_policy_list', methods=('GET', 'POST'))
def get_istio_policy_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("收到的数据;{}".format(data))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="security.istio.io", version="v1beta1",
                                                      plural="authorizationpolicies")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace, group="security.istio.io",
                                                         version="v1beta1", plural="authorizationpolicies")
    except ApiException as e:
        if isinstance(e.body, dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            message = e.body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        # current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})
    policys = obj['items']
    policy_list = []
    i = 0
    for policy in policys:
        if (i >= 0):
            print(policy)
            meta = policy['metadata']
            spec = policy['spec']
            print(spec)
            name = meta['name']
            namespace = meta['namespace']
            time_str = meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')
            # if spec != {} or spec != None:

            my_policy={}
            my_policy["name"] = name
            my_policy["namespace"] = namespace
            my_policy["spec"] = spec
            # my_policy["name"] = name
            my_policy["create_time"] = create_time
            policy_list.append(my_policy)
        i = i + 1
    return json.dumps(policy_list, indent=4, cls=MyEncoder)
    # return jsonify({"ok":"get policy list"})

@k8s.route('/delete_istio_policy', methods=('GET', 'POST'))
def delete_istio_policy():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.CustomObjectsApi()
    try:
        api_response = myclient.delete_namespaced_custom_object(group="security.istio.io",
                                                                version="v1beta1",
                                                                plural="authorizationpolicies",
                                                                namespace=namespace,
                                                                name=name,
                                                                body=client.V1DeleteOptions(
                                                                    propagation_policy='Foreground',
                                                                    grace_period_seconds=5))

        # print(api_response)
        result = "{}".format(api_response)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除异常',"msg":msg})
    return jsonify({"ok":"删除成功"})