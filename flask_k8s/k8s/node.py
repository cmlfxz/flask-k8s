

from flask import Flask,jsonify,request,current_app
import json
from flask_k8s.util import *
from flask_k8s.k8s_decode import MyEncoder
from kubernetes import client,config
from kubernetes.client.rest import ApiException

# 导入蓝图
from flask_k8s.k8s import k8s


# @k8s_op.route('/get_node_by_name', methods=('GET', 'POST'))
def get_node_by_name(name=None):
    params = {}
    params['label_selector'] = {"kubernetes.io/role": "master"}
    # field_selector='metadata.name=192.168.11.52'
    # label_selector="kubernetes.io/role=master"
    # name = "192.168.11.52"
    field_selector="{}={}".format("metadata.name",name)
    node = None
    node_list = client.CoreV1Api().list_node(limit=1,field_selector=field_selector)

    for item in node_list.items:
        if item.metadata.name == name:
            node = item
            break
    return node

@k8s.route('/update_node', methods=('GET', 'POST'))
def update_node():
    data=json.loads(request.get_data().decode('utf-8'))
    print("update_node接收到的数据是{}".format(data))
    name=handle_input(data.get("node_name"))
    action=handle_input(data.get("action"))
    
    node  = get_node_by_name(name)
    if node == None:
        return jsonify({"error":"找不到此node信息"})
    if action=="add_taint":
        print("正在添加node污点")
        effect = handle_input(data.get('taint_effect'))
        key = handle_input(data.get('taint_key'))   
        value = handle_input(data.get('taint_value'))
        # print(type(node.spec.taints))
        if node.spec.taints == None:
            node.spec.taints = []
        taint = client.V1Taint(effect=effect,key=key,value=value)
        node.spec.taints.append(taint)
        # print(node.spec.taints)
    elif action=="delete_taint":
        print("正在删除node污点")
        effect = handle_input(data.get('taint_effect'))
        key = handle_input(data.get('taint_key'))
        value = handle_input(data.get('taint_value'))
        # print(key,value)
        # print(type(node.spec.taints))
        if node.spec.taints == None:
            return jsonify({"error":"taint列表为空"})
        # 查找元素
        i = -1
        taint_len = len(node.spec.taints)
        has_taint = False
        for taint in node.spec.taints:
            i = i + 1
            # print(taint)
            if effect == taint.effect and key==taint.key and value ==taint.value:
                has_taint = True
                break
        #查找元素
        if not has_taint:
            return jsonify({"error": "没有此taint"})
        else:
            node.spec.taints.pop(i)
            # print(node.spec.taints)
    elif action=="update_taint":
        print("正在更新node污点")
        old_effect = handle_input(data.get('old_taint_effect'))
        old_key = handle_input(data.get('old_taint_key'))
        old_value = handle_input(data.get('old_taint_value'))
        new_effect = handle_input(data.get('taint_effect'))
        new_key = handle_input(data.get('taint_key'))
        new_value = handle_input(data.get('taint_value'))
        
        if node.spec.taints == None:
            node.spec.taints = []
        new_taint = client.V1Taint(effect=new_effect,key=new_key,value=new_value)
        # print(new_taint)
        # 思路，找到index，替换
        # 查找元素
        i = -1
        taint_len = len(node.spec.taints)
        has_taint = False
        for taint in node.spec.taints:
            i = i + 1
            # print(taint)
            if old_effect == taint.effect and old_key==taint.key and old_value ==taint.value:
                has_taint = True
                break
        #查找元素
        if not has_taint:
            return jsonify({"error": "没有此taint"})
        else:
            node.spec.taints[i] = new_taint
            # print(node.spec.taints)
    #增加标签
    elif action == "add_labels":
        current_app.logger.debug("正在执行:{}".format(action))
        #{"a":1,"b":2}
        input_labels = handle_input(data.get('labels'))
        current_app.logger.debug("接收到的数据:{}".format(input_labels))
        if input_labels == None:
            return simple_error_handle("没有收到labels")
        labels = node.metadata.labels
        current_app.logger.debug(type(labels),labels)
        for k, v in input_labels.items():
            labels[k] = v
        node.metadata.labels = labels
    elif action == "delete_labels":
        current_app.logger.debug("正在执行:{}".format(action))
        #{"a":1,"b":2}
        input_labels = handle_input(data.get('labels'))
        current_app.logger.debug("接收到的数据:{}".format(input_labels))
        if input_labels == None:
            return simple_error_handle("没有收到labels")
        labels = node.metadata.labels
        current_app.logger.debug(type(labels),labels)
        for k, v in input_labels.items():
            labels.pop(k)
        current_app.logger.debug("移除标签后:{}".format(labels))
        node.metadata.labels = labels
    else:
        return jsonify({"error":"不支持此动作{}".format(action)})
    try:
        if action == "delete_labels":
            result = client.CoreV1Api().replace_node(name=name, body=node)
        else:
            result = client.CoreV1Api().patch_node(name=name,body=node)
    except ApiException as e:
        body = json.loads(e.body)
        msg = {"status": e.status, "reason": e.reason, "message": body['message']}
        return jsonify({'error': '更新node失败', "msg": msg})

    return jsonify({"ok": "{}成功".format(action)})
