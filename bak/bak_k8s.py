@k8s.route('/get_gw_list')
def get_gw_list():
    gw_url = "https://192.168.11.51:6443/apis/networking.istio.io/v1alpha3/gateways"
    
    public_cert = os.path.join(dir_path,'admin.pem')
    private_cert = os.path.join(dir_path,'admin-key.pem')
    ca_cert =  os.path.join(dir_path,'ca.pem')
    result = requests.get(gw_url,cert=(public_cert,private_cert),verify=ca_cert)
    # result = requests.get(gw_url,verify=False)
    print(result.status_code)
    obj = json.loads(result.content)
    #obj是一个字典
    # print(type(obj))
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
            print(type(meta))
            print(spec)
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


#列出gateway
@k8s.route('/get_gateway_list')
def get_gateway_list():
    # myclient = client.NetworkingV1beta1Api()
    # myclient.list
    # i = 0 
    gateway_url = "http://192.168.11.51:1900/apis/networking.istio.io/v1alpha3/gateways"
    #带命名空间的
    #http://192.168.11.51:1900/apis/networking.istio.io/v1alpha3/namespaces/ms-prod/gateways
    result = requests.get(gateway_url)
    print(result.status_code)
    # print(result.content)
    obj = json.loads(result.content)
    #obj是一个字典
    # print(type(obj))
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
            print(type(meta))
            print(spec)
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
    # myclient = client.NetworkingV1beta1Api()
    # myclient.list
    # i = 0 
    virtual_service_url = "http://192.168.11.51:1900/apis/networking.istio.io/v1alpha3/virtualservices"
    #带命名空间的
    # virtual_service_url = "http://192.168.11.51:1900/apis/networking.istio.io/v1alpha3/namespaces/ms-prod/virtualservices"
    result = requests.get(virtual_service_url)
    print(result.status_code)
    obj = json.loads(result.content)
    #obj是一个字典
    virtual_services = obj['items']
    # print(type(virtual_services))
    virtual_service_list = []
    i = 0
    for virtual_service in virtual_services:
        if(i>=0):
            # print(type(virtual_service))
            print(virtual_service)
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
    # myclient = client.NetworkingV1beta1Api()
    # myclient.list
    # i = 0 
    destination_rule_url = "http://192.168.11.51:1900/apis/networking.istio.io/v1alpha3/destinationrules"
    #带命名空间的
    # destination_rule_url = "http://192.168.11.51:1900/apis/networking.istio.io/v1alpha3/namespaces/ms-prod/destinationrules"
    result = requests.get(destination_rule_url)
    print(result.status_code)
    obj = json.loads(result.content)
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
    
    
@k8s.route('/get_deployment_list',methods=('GET','POST'))
def get_deployment_list():
    data = json.loads(request.get_data().decode("utf-8"))
    namespace = data.get("namespace").strip()
    myclient = client.AppsV1Api()
    if namespace == "" or namespace == "all": 
        deployments = myclient.list_deployment_for_all_namespaces(watch=False)
    else:
        deployments = myclient.list_namespaced_deployment(namespace=namespace)
    
    # myclient = client.AppsV1Api()
    # deployments = myclient.list_namespaced_deployment("ms-dev")
    i = 0
    
    deployment_list = []
    for deployment in deployments.items:
        if (i>=0):
            print(deployment)
            meta = deployment.metadata
            name = meta.name
            create_time = time_to_string(meta.creation_timestamp)
            cluster_name = meta.cluster_name
            # labels = format_dict(meta.labels)
            labels = meta.labels
            # print(labels)
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
            
            container_names = []
            container_images = []
            for container in containers:
                c_name  = container.name 
                c_image = container.image
                container_names.append(c_name)
                container_images.append(c_image)
            # env = containers.env
            image_pull_secrets = template_spec.image_pull_secrets[0]
            host_network = template_spec.host_network
            node_selector = template_spec.node_selector
            
            service_account_name = template_spec.service_account_name
            tolerations = template_spec.tolerations
            
            status = deployment.status
            ready = "{}/{}".format(status.ready_replicas,status.replicas)
            mystatus = {"ready":ready,"available_replicas":status.available_replicas,\
            "up-to-date":status.updated_replicas}
            
            mydeployment = {"name":name,"replicas":replicas,"namespace":namespace,\
                "container_names":container_names,"container_images":container_images,"status":mystatus,"labels":labels,"labels":template_labels,"create_time":create_time}
            # mydeployment = {"name":name,"namespace":namespace,"status":mystatus,"labels":labels,"replicas":replicas,"labels":template_labels,"containers":containers,\
            #     "affinity":affinity,"tolerations":tolerations,"node_selector":node_selector,"host_network":host_network,"strategy":strategy,"image_pull_secrets":image_pull_secrets,\
            #     "service_account_name":service_account_name,"create_time":create_time}
            
            deployment_list.append(mydeployment)
            
        i = i +1       
    return json.dumps(deployment_list,indent=4,cls=DateEncoder)
    # return json.dumps(deployment_list,default=lambda obj: obj.__dict__,indent=4)

# def create_deployment_object(name,image,port,image_pull_policy,labels,replicas):
#     #configure pod template container
#     container = client.V1Container(
#         name="nginx",
#         image="nginx:1.15.4",
#         image_pull_policy="IfNotPresent",
#         ports=[client.V1ContainerPort(container_port=80,name="http",protocol="http")]
#         #probe
#         #resources
#         #volume_mounts 
#         #env
#     )
#     template = client.V1PodTemplateSpec(
#         metadata=client.V1ObjectMeta(labels={"app":"nginx"}),
#         spec=client.V1PodSpec(containers=[container])
#     )
#     spec = client.V1DeploymentSpec(
#         replicas=3,
#         template=template,
#         selector={'matchLabels':{'app':'nginx'}}
#         #strategy
#     )
#     deployment = client.V1Deployment(
#         api_version="apps/v1",
#         kind="Deployment",
#         metadata=client.V1ObjectMeta(name=DEPLOYMENT_NAME),
#         spec=spec
#     )
#     return deployment

# def get_dr_by_name(namespace,dr_name):
#     virtual_services = client.CustomObjectsApi().list_namespaced_custom_object(group="networking.istio.io",
#                                                                                version="v1alpha3",
#                                                                                plural="virtualservices",namespace=namespace)
#     virtual_service = None
#     for dr in virtual_services.items:
#         if dr.metadata.name == dr_name:
#             virtual_service = dr
#             break 
#     return virtual_service
            
    
# def update_dr(dr_name,namespace=namespace,prod_weight,canary_weight):
#     myclient = client.CustomObjectsApi()
#     #先获取到对应的dr名称
#     dr = get_dr_by_name(namespace,dr_name)
#     if dr == None:
#         return jsonify({"error":"1003","msg":"找不到该dr"})
#     # dr.spec.
#     myclient.patch_namespaced_custom_object(namespace=namespace,
#                                             group="networking.istio.io",
#                                             version="v1alpha3",
#                                             plural="virtualservices",
#                                             body=dr)


# sql = Cluster.query.filter(Cluster.cluster_name==cluster_name)
# 纯粹测试
# sql = db.session.query(Cluster.cluster_config).filter(Cluster.cluster_name==cluster_name)
# if sql.first():
#     cluster_config  = my_decode(sql.first().cluster_config)
#     print("从数据库读取的配置: \n{}".format(cluster_config))
#     tmp_filename = "kubeconfig"
#     with open(tmp_filename,'w+',encoding='UTF-8') as file:
#         file.write(cluster_config)
#     #这里需要一个文件
#     config.load_kube_config(config_file=tmp_filename)
    
#     list_dict = []

#     for api in client.ApisApi().get_api_versions().groups:
#         print(api)
#         versions = []
#         for v in api.versions:
#             name  = ""
#             if v.version == api.preferred_version.version and len(api.versions) > 1:
#                 name += "*"
#             name += v.version
#             versions.append(name)
#             #存到字典里面去  
#         dict1 = {'name': api.name,'versions':",".join(versions)}
#         list_dict.append(dict1)
#     # list_dict.sort(key=takename)
#     return jsonify(list_dict)