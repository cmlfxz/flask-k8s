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
from flask_k8s.task import task

@task.route('/get_job_list',methods=('GET','POST'))
def get_job_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.BatchV1Api()
    if namespace == "" or namespace == "all": 
        jobs = myclient.list_job_for_all_namespaces(watch=False)
    else:
        jobs = myclient.list_namespaced_job(namespace=namespace)
    # myclient = client.BatchV1Api()
    # jobs = myclient.list_job_for_all_namespaces()
    job_list = []
    i = 0 
    for job in jobs.items:
        if (i >=0):
            # print(job)
            meta = job.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
                   
            status = job.status
            active = status.active
            succeeded = status.succeeded
            start_time = time_to_string(status.start_time)
            completion_time = time_to_string(status.completion_time)
            
            mystatus = {"active":active,"succeeded":succeeded,"start_time":start_time,"completion_time":completion_time}
            
            myjob = {"name":name,"namespace":namespace,"status":mystatus,"labels":labels,"create_time":create_time}
            job_list.append(myjob) 
        i = i +1
    return json.dumps(job_list,indent=4,cls=MyEncoder)

#列出job
@task.route('/get_cronjob_list',methods=('GET','POST'))
def get_cronjob_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.BatchV1beta1Api()
    if namespace == "" or namespace == "all": 
        cronjobs = myclient.list_cron_job_for_all_namespaces(watch=False)
    else:
        cronjobs = myclient.list_namespaced_cron_job(namespace=namespace)
    cronjob_list = []
    i = 0 
    for cronjob in cronjobs.items:
        if (i >=0):
            # print(cronjob)
            meta = cronjob.metadata
            name = meta.name 
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            labels = meta.labels
            namespace = meta.namespace 
            
            spec = cronjob.spec
            schedule = spec.schedule
            successful_jobs_history_limit = spec.successful_jobs_history_limit
            suspend = spec.suspend
            status = cronjob.status
            active = status.active
            last_schedule_time = time_to_string(status.last_schedule_time)
            
            mystatus = {"active":active,"last_schedule_time":last_schedule_time}
            
            mycronjob = {"name":name,"namespace":namespace,"schedule":schedule,"status":mystatus,"labels":labels,\
                "successful_jobs_history_limit":successful_jobs_history_limit, "suspend":suspend,"create_time":create_time}
            cronjob_list.append(mycronjob) 
        i = i +1
    return json.dumps(cronjob_list,indent=4,cls=MyEncoder)




@task.route('/delete_job', methods=('GET', 'POST'))
def delete_job():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.BatchV1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_job(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除job异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

@task.route('/delete_cronjob', methods=('GET', 'POST'))
def delete_cronjob():
    data = json.loads(request.get_data().decode('utf-8'))
    name  = handle_input(data.get('name'))
    namespace = handle_input(data.get('namespace'))
    myclient = client.BatchV1beta1Api()
    try:
        # body=client.V1DeleteOptions(propagation_policy='Foreground',grace_period_seconds=5)
        result = myclient.delete_namespaced_cron_job(namespace=namespace,name=name)
    except Exception as e:
        body = json.loads(e.body)
        msg={"status":e.status,"reason":e.reason,"message":body['message']}
        # return simple_error_handle(msg)
        return jsonify({'error': '删除cronjob异常',"msg":msg})
    return jsonify({"ok":"删除成功"})

