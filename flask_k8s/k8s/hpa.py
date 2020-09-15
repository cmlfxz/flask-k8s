from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from flask_k8s.k8s_decode import MyEncoder
from flask_k8s.util import *
from kubernetes import client,config
from kubernetes.client.rest import ApiException
# from kubernetes.client.models.v1_namespace import V1Namespace

# 导入蓝图
from flask_k8s.k8s import k8s


@k8s.route('/get_hpa_list',methods=('GET','POST'))
def get_hpa_list():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收的数据:{}".format(data))
    namespace = handle_input(data.get("namespace"))
    myclient = client.AutoscalingV1Api()
    if namespace == "" or namespace == "all":
        hpas = myclient.list_horizontal_pod_autoscaler_for_all_namespaces()
    else:
        hpas =myclient.list_namespaced_horizontal_pod_autoscaler(namespace=namespace)
    # print(type(hpas.items))
    hpa_list = []
    for hpa in hpas.items:
        # print(hpa)
        meta  = hpa.metadata
        name = meta.name
        namespace = meta.namespace
        spec = hpa.spec
        maxReplicas = spec.max_replicas
        minReplicas = spec.min_replicas
        scaleTargetRef = spec.scale_target_ref
        targetCPUUtilizationPercentage = spec.target_cpu_utilization_percentage

        myhpa= {}
        myhpa["name"] =name
        myhpa["namespace"] =namespace
        myhpa["minReplicas"] =minReplicas

        myhpa["maxReplicas"] =maxReplicas

        myhpa["scaleTargetRef"] =scaleTargetRef
        myhpa["targetCPUUtilizationPercentage"] =targetCPUUtilizationPercentage

        # print(myhpa)
        hpa_list.append(myhpa)
    # return json.dumps({"ok":"123"})
    return json.dumps(hpa_list,indent=4,cls=MyEncoder)


@k8s.route('/delete_hpa', methods=('GET', 'POST'))
def delete_hpa():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.AutoscalingV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_horizontal_pod_autoscaler(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除hpa异常',"msg":msg})
    return jsonify({"ok":"删除成功"})