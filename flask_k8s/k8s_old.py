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