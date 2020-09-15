from flask import Flask,jsonify,Response,make_response,Blueprint,request,g,current_app
from flask_cors import *
from dateutil import tz, zoneinfo
from datetime import datetime,date
from flask_k8s.k8s_decode import MyEncoder
import json,os,math,requests,time,pytz,ssl,yaml
from flask_k8s.util import *
from kubernetes import client,config
from kubernetes.client.rest import ApiException
# from kubernetes.client.models.v1_namespace import V1Namespace

# 导入蓝图
from flask_k8s.storage import storage
#列出storageclass
@storage.route('/get_storageclass_list',methods=('GET','POST'))
def get_storageclass_list():
    myclient = client.StorageV1Api()
    storageclasss = myclient.list_storage_class()
    storageclass_list = []
    i = 0 
    for sc in storageclasss.items:
        if (i >= 0):
            # print(sc)
            meta = sc.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            # annotations = meta.annotations
            mount_options = sc.mount_options
            parameters = sc.parameters
            provisioner = sc.provisioner
            reclaim_policy = sc.reclaim_policy
            
            volume_binding_mode = sc.volume_binding_mode
            mysc = {"name":name,"provisioner":provisioner,"reclaim_policy":reclaim_policy,\
                            "parameters":parameters,\
                            "mount_options":mount_options,"volume_binding_mode":volume_binding_mode,"create_time":create_time}    
            storageclass_list.append(mysc) 
        i = i +1
    return json.dumps(storageclass_list,indent=4,cls=MyEncoder)

#列出pv
@storage.route('/get_pv_list',methods=('GET','POST'))
def get_pv_list():
    myclient = client.CoreV1Api()
    pvs = myclient.list_persistent_volume()
    pv_list = []
    i = 0 
    for pv in pvs.items:
        if (i >= 0):
            # print(pv)
            meta = pv.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
 
            spec = pv.spec
            
            access_modes = spec.access_modes[0]
            capacity = spec.capacity['storage']
            nfs = spec.nfs
            cephfs = spec.cephfs
            flexVolume = spec.flex_volume
            glusterfs = spec.glusterfs
            rbd = spec.rbd
            hostPath = spec.host_path
            
            source = None
            if nfs:
                source=nfs
            elif hostPath:
                source=hostPath
            elif rbd:
                source=rbd
            elif flexVolume:
                source = flexVolume
            elif glusterfs:
                source = glusterfs
            else:
                pass
            
            mountOptions = spec.mount_options
            pv_reclaim_policy = spec.persistent_volume_reclaim_policy
            storage_class_name = spec.storage_class_name
            volume_mode = spec.volume_mode
            claim_ref = spec.claim_ref
            pvc_namespace = pvc_name = None
            if claim_ref:
                pvc_namespace = claim_ref.namespace
                pvc_name = claim_ref.name
            pvc = "{}/{}".format(pvc_namespace,pvc_name)

            status = pv.status.phase

            info = {}
            info["capacity"] = capacity
            info["access_modes"] = access_modes
            info["pv_reclaim_policy"] = pv_reclaim_policy
            info["volume_mode"] = volume_mode

            my_pv = {}
            my_pv["name"] = name
            my_pv["pvc"] = pvc
            my_pv["status"] = status
            my_pv["info"] = info
            my_pv["storage_class_name"] = storage_class_name
            my_pv["source"] = source
            my_pv["create_time"] = create_time

            pv_list.append(my_pv) 
        i = i +1
    return json.dumps(pv_list,indent=4,cls=MyEncoder)

#列出pvc
@storage.route('/get_pvc_list',methods=('GET','POST'))
def get_pvc_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.CoreV1Api()
    if namespace == "" or namespace == "all": 
        pvcs = myclient.list_persistent_volume_claim_for_all_namespaces(watch=False)
    else:
        pvcs = myclient.list_namespaced_persistent_volume_claim(namespace=namespace)
    pvc_list = []
    i = 0 
    for pvc in pvcs.items:
        if (i >= 0):
            # print(pvc)
            meta = pvc.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            namespace = meta.namespace
 
            spec = pvc.spec
            
            access_modes = spec.access_modes[0]
            resources = spec.resources
            capacity = resources.requests['storage']
            storage_class_name = spec.storage_class_name
            volume_name = spec.volume_name

            # status = pvc.status
            phase = pvc.status.phase
            # volume_binding_mode = pvc.volume_binding_mode
            my_pvc = {}
            my_pvc["name"] = name
            my_pvc["namespace"] = namespace
            my_pvc["pv"] = volume_name
            my_pvc["status"] = phase
            my_pvc["capacity"] = capacity
            my_pvc["resources"] = resources
            my_pvc["access_modes"] = access_modes
            my_pvc["storage_class_name"] = storage_class_name
            my_pvc["create_time"] = create_time
            pvc_list.append(my_pvc)
        i = i +1
    return json.dumps(pvc_list,indent=4,cls=MyEncoder)


def create_pv_object(name,**kwargs):
    for k,v in kwargs.items():
        print ('Optional key: %s value: %s' % (k, v))
    capacity = kwargs['capacity']
    accessModes = kwargs['accessModes']
    reclaimPolicy = kwargs['reclaimPolicy']
    storage_class_name = kwargs['storage_class_name']
    nfs = kwargs['nfs']
    # current_app.logger.debug("nfs: {}".format(nfs))
    nfs_path = nfs['path']
    nfs_server = nfs['server']
    readonly = nfs['readonly']
    
    nfs_readonly = False
    if readonly == 'true':
        nfs_readonly = True
    elif readonly == 'false':
        nfs_readonly == False
    else:
        pass
    spec = client.V1PersistentVolumeSpec(
        access_modes = [accessModes],
        capacity = {"storage":capacity},
        persistent_volume_reclaim_policy = reclaimPolicy,
        nfs = client.V1NFSVolumeSource(
            path = nfs_path,
            server = nfs_server,
            read_only = nfs_readonly
        ),
        storage_class_name=storage_class_name,
    )
    # print(spec)
    pv = client.V1PersistentVolume(
        api_version="v1",
        kind="PersistentVolume",
        metadata=client.V1ObjectMeta(name=name),
        spec=spec)
    return pv

@storage.route('/create_pv',methods=('GET','POST'))
def create_pv():
    data = json.loads(request.get_data().decode("utf-8"))
    current_app.logger.debug("接收到的数据:{}".format(data))
    name = handle_input(data.get('name'))

    pv =  handle_input(data.get('pv'))
    capacity = pv['capacity']
    accessModes = pv['accessModes']
    reclaimPolicy = pv['reclaimPolicy']
    storage_class_name = pv['storage_class_name']
    nfs  = pv['nfs']

    pv = create_pv_object(name=name,capacity=capacity,accessModes=accessModes,\
            reclaimPolicy=reclaimPolicy,storage_class_name=storage_class_name,nfs=nfs)
    current_app.logger.debug(pv)
    myclient = client.CoreV1Api()
    try:
        api_response = myclient.create_persistent_volume(body=pv)
    except ApiException as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '创建失败',"msg":msg})
    
    return jsonify({"ok":"创建pv成功"})


@storage.route('/delete_pv', methods=('GET', 'POST'))
def delete_pv():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    myclient = client.CoreV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_persistent_volume(name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除PVC异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@storage.route('/delete_multi_pv', methods=('GET', 'POST'))
def delete_multi_pv():
    data = json.loads(request.get_data().decode('utf-8'))
    try:
        list = data['pv_list']
        # print(list)
    except Exception as e:
        print(e)
        return jsonify({"fail ":e})
    myclient = client.CoreV1Api()
    for name in list:
        try:
            # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
            result = myclient.delete_persistent_volume(name=name)
        except Exception as e:
            body = json.loads(e.body)
            msg={"status":e.status,"reason":e.reason,"message":body['message']}
            # return simple_error_handle(msg)
            return jsonify({'error': '删除PV异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@storage.route('/delete_pvc', methods=('GET', 'POST'))
def delete_pvc():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace  = handle_input(data.get('namespace'))
    if namespace == '' or namespace == 'all':
        return simple_error_handle("namespace不能为空，并且不能选择all")
    myclient = client.CoreV1Api()
    try:
        result = myclient.delete_namespaced_persistent_volume_claim(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        return jsonify({'error': '删除PV异常',"msg":msg})
    return jsonify({"ok":"删除成功"})