

from flask import Flask,jsonify,request,current_app
import json,requests
from flask_k8s.util import *
from flask_k8s.k8s_decode import MyEncoder
from kubernetes import client,config
from kubernetes.client.rest import ApiException


# 导入蓝图
from flask_k8s.k8s import k8s

# 列出gateway
@k8s.route('/get_gateway_list', methods=('GET', 'POST'))
def get_gateway_list():
    # myclient = client.CustomObjectsApi()
    # obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="gateways")
    data = json.loads(request.get_data().decode("utf-8"))
    # current_app.logger.debug("get_gateway_list收到的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.CustomObjectsApi()
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="networking.istio.io", version="v1alpha3",
                                                      plural="gateways")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace, group="networking.istio.io",
                                                         version="v1alpha3", plural="gateways")
    except ApiException as e:
        if isinstance(e.body, dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            body = e.body
            message = body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        # current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})
    gateways = obj['items']
    gateway_list = []
    i = 0
    for gateway in gateways:
        if (i >= 0):
            meta = gateway['metadata']
            spec = gateway['spec']
            name = meta['name']
            namespace = meta['namespace']
            time_str = meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')
            # Unixtime = time.mktime(time.strptime(time_str, '%Y-%m-%dT%H:%M:%SZ'))
            # create_time = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(Unixtime))
            selector = spec['selector']
            servers = spec['servers']
            domain_list = []
            for server in servers:
                domain = server['hosts']
                domain_list.append(domain)

            mygateway = {"name": name, "namespace": namespace, "selector": selector, "servers": servers,
                         "domain_list": domain_list, "create_time": create_time, }
            gateway_list.append(mygateway)
        i = i + 1
    return json.dumps(gateway_list, indent=4, cls=MyEncoder)

# 列出vs
@k8s.route('/get_virtual_service_list', methods=('GET', 'POST'))
def get_virtual_service_list():
    # myclient = client.CustomObjectsApi()
    # obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="virtualservices")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    # bug 没有vs的集群报错404，页面没具体显示
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="networking.istio.io", version="v1alpha3",
                                                      plural="virtualservices")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace, group="networking.istio.io",
                                                         version="v1alpha3", plural="virtualservices")
    except ApiException as e:
        if isinstance(e.body, dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            body = e.body
            message = body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        # current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})

    virtual_services = obj['items']
    virtual_service_list = []
    i = 0
    for virtual_service in virtual_services:
        if (i >= 0):
            meta = virtual_service['metadata']
            spec = virtual_service['spec']
            name = meta['name']
            namespace = meta['namespace']
            time_str = meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')
            try:
                gateways = spec['gateways']
            except Exception as e:
                gateways = None
                # print(e)
            hosts = spec['hosts']
            http = spec['http']
            myvirtual_service = {"name": name, "namespace": namespace, "gateways": gateways, "hosts": hosts,
                                 "http": http, "create_time": create_time, }
            virtual_service_list.append(myvirtual_service)

        i = i + 1
    return json.dumps(virtual_service_list, indent=4)
    # return json.dumps(virtual_service_list,indent=4,cls=MyEncoder)

def get_vs_by_name(namespace, vs_name):
    virtual_services = client.CustomObjectsApi().list_namespaced_custom_object(group="networking.istio.io",
                                                                               version="v1alpha3",
                                                                               plural="virtualservices",
                                                                               namespace=namespace)
    virtual_service = None
    for vs in virtual_services['items']:
        if vs['metadata']['name'] == vs_name:
            virtual_service = vs
            break
    return virtual_service

def update_virtual_service(vs_name, namespace, prod_weight, canary_weight):
    myclient = client.CustomObjectsApi()
    # 先获取到对应的vs名称
    vs = get_vs_by_name(namespace, vs_name)
    if vs == None:
        return jsonify({"error": "1003", "msg": "找不到该vs"})
    # print(vs)
    # 这样必须规定第一条route是生产版本，第二条是灰度版本
    # print(vs['spec']['http'][0]['route'][0]['weight'])
    # print(vs['spec']['http'][0]['route'][1]['weight'])
    try:
        vs['spec']['http'][0]['route'][0]['weight'] = prod_weight
        vs['spec']['http'][0]['route'][1]['weight'] = canary_weight
        api_response = myclient.patch_namespaced_custom_object(group="networking.istio.io",
                                                               version="v1alpha3",
                                                               plural="virtualservices",
                                                               name=vs_name,
                                                               namespace=namespace,
                                                               body=vs)
        # print(api_response['spec'])
        status = "{}".format(api_response['spec']['http'])
    except Exception as e:
        print(e)
        return jsonify({"异常": "可能非生产环境，没有设置灰度"})

    return jsonify({"update_status": status})

@k8s.route('/update_vs', methods=('GET', 'POST'))
def update_vs():
    data = json.loads(request.get_data().decode('UTF-8'))
    print("接受到的数据:{}".format(data))
    namespace = handle_input(data.get('namespace'))
    vs_name = handle_input(data.get('vs_name'))
    # print(type(data.get('canary_weight')))
    canary_weight = math.ceil(str_to_int(handle_input(data.get('canary_weight'))))
    if (canary_weight < 0 or canary_weight > 100):
        return jsonify({"error": 1003, "msg": "灰度值需在1-100之间"})
    prod_weight = 100 - canary_weight
    return update_virtual_service(vs_name=vs_name, namespace=namespace, prod_weight=prod_weight,
                                  canary_weight=canary_weight)


@k8s.route('/delete_vs', methods=('GET', 'POST'))
def delete_vs():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('virtual_service_name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.CustomObjectsApi()
    try:
        result = myclient.delete_namespaced_custom_object(group="networking.istio.io",
                                                            version="v1alpha3",
                                                            plural="virtualservices",
                                                            namespace=namespace,
                                                            name=name,
                                                            body=client.V1DeleteOptions(propagation_policy='Foreground',
                                                                                        grace_period_seconds=5))
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除vs异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@k8s.route('/get_destination_rule_list', methods=('GET', 'POST'))
def get_destination_rule_list():
    # myclient = client.CustomObjectsApi()
    # obj = myclient.list_cluster_custom_object(group="networking.istio.io",version="v1alpha3",plural="destinationrules")
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CustomObjectsApi()
    try:
        if namespace == "" or namespace == "all":
            obj = myclient.list_cluster_custom_object(group="networking.istio.io", version="v1alpha3",
                                                      plural="destinationrules")
        else:
            obj = myclient.list_namespaced_custom_object(namespace=namespace, group="networking.istio.io",
                                                         version="v1alpha3", plural="destinationrules")
    except ApiException as e:
        if isinstance(e.body, dict):
            body = json.loads(e.body)
            message = body['message']
        else:
            body = e.body
            message = body
        msg = {"status": e.status, "reason": e.reason, "message": message}
        current_app.logger.debug(msg)
        return jsonify({'error': '获取列表失败', "msg": msg})
    # obj是一个字典
    drs = obj['items']
    dr_list = []
    i = 0
    for dr in drs:
        if (i >= 0):
            # print(dr)
            meta = dr['metadata']
            spec = dr['spec']
            name = meta['name']
            namespace = meta['namespace']
            time_str = meta['creationTimestamp']
            create_time = utc_to_local(time_str, utc_format='%Y-%m-%dT%H:%M:%SZ')

            host = spec['host']
            subsets = None
            if 'subsets' in spec.keys():
                subsets = spec['subsets']
            trafficPolicy = None
            if 'trafficPolicy' in spec.keys():
                trafficPolicy = spec['trafficPolicy']
            my_dr = {}
            my_dr = {"name": name, "namespace": namespace, "host": host, "subsets": subsets}
            my_dr['trafficPolicy'] = trafficPolicy
            my_dr['create_time'] = create_time
            dr_list.append(my_dr)

        i = i + 1
    return json.dumps(dr_list, indent=4, cls=MyEncoder)


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