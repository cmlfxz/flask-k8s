import json
from datetime import date,datetime 

from kubernetes.client.models.v1_taint import V1Taint
from kubernetes.client.models.v1_node_system_info import V1NodeSystemInfo
from kubernetes.client.models.v1_label_selector import V1LabelSelector
from kubernetes.client.models.v1_deployment_strategy import V1DeploymentStrategy
from kubernetes.client.models.v1_rolling_update_deployment import V1RollingUpdateDeployment
from kubernetes.client.models.v1_local_object_reference import V1LocalObjectReference
from kubernetes.client.models.v1_container import V1Container
from kubernetes.client.models.v1_container_port import V1ContainerPort
from kubernetes.client.models.v1_volume_mount import V1VolumeMount
from kubernetes.client.models.v1_env_var import V1EnvVar
from kubernetes.client.models.v1_env_var_source import V1EnvVarSource
from kubernetes.client.models.v1_secret_key_selector import V1SecretKeySelector
from kubernetes.client.models.v1_probe import V1Probe
from kubernetes.client.models.v1_tcp_socket_action import V1TCPSocketAction
from kubernetes.client.models.v1_http_get_action import V1HTTPGetAction
from kubernetes.client.models.v1_affinity import V1Affinity
from kubernetes.client.models.v1_node_affinity import V1NodeAffinity
from kubernetes.client.models.v1_node_selector import V1NodeSelector
from kubernetes.client.models.v1_node_selector_term import V1NodeSelectorTerm
from kubernetes.client.models.v1_node_selector_requirement import V1NodeSelectorRequirement
from kubernetes.client.models.v1_object_field_selector import V1ObjectFieldSelector
from kubernetes.client.models.v1_toleration import V1Toleration
from kubernetes.client.models.v1_nfs_volume_source import V1NFSVolumeSource
from kubernetes.client.models.v1_object_reference import V1ObjectReference
from kubernetes.client.models.v1_persistent_volume_claim_status import V1PersistentVolumeClaimStatus
from kubernetes.client.models.v1_resource_requirements import V1ResourceRequirements
from kubernetes.client.models.v1_service_port import V1ServicePort
from kubernetes.client.models.v1_service_status import V1ServiceStatus
from kubernetes.client.models.v1_load_balancer_status import V1LoadBalancerStatus
from kubernetes.client.models.v1_pod_security_context import V1PodSecurityContext
from kubernetes.client.models.extensions_v1beta1_ingress_rule import ExtensionsV1beta1IngressRule
from kubernetes.client.models.extensions_v1beta1_http_ingress_rule_value import ExtensionsV1beta1HTTPIngressRuleValue
from kubernetes.client.models.extensions_v1beta1_http_ingress_path import ExtensionsV1beta1HTTPIngressPath
from kubernetes.client.models.extensions_v1beta1_ingress_backend import ExtensionsV1beta1IngressBackend
from kubernetes.client.models.extensions_v1beta1_ingress_tls import ExtensionsV1beta1IngressTLS
from kubernetes.client.models.v1_deployment import V1Deployment
from kubernetes.client.models.v1_object_meta import V1ObjectMeta
from kubernetes.client.models.v1_deployment_spec import V1DeploymentSpec
from kubernetes.client.models.v1_pod_template_spec import V1PodTemplateSpec
from kubernetes.client.models.v1_pod_spec import V1PodSpec
from kubernetes.client.models.v1_volume import V1Volume
from kubernetes.client.models.v1_empty_dir_volume_source import V1EmptyDirVolumeSource
from kubernetes.client.models.extensions_v1beta1_ingress_list import ExtensionsV1beta1IngressList
from kubernetes.client.models.v1_preferred_scheduling_term import V1PreferredSchedulingTerm
from kubernetes.client.models.v1_config_map_key_selector import V1ConfigMapKeySelector
from kubernetes.client.models.v1_pod_anti_affinity import V1PodAntiAffinity
from kubernetes.client.models.v1_pod_affinity_term import V1PodAffinityTerm
from kubernetes.client.models.v1_weighted_pod_affinity_term import V1WeightedPodAffinityTerm
from kubernetes.client.models.v1_label_selector import V1LabelSelector
from kubernetes.client.models.v1_label_selector_requirement import V1LabelSelectorRequirement
from kubernetes.client.models.v1_namespace import V1Namespace
from kubernetes.client.models.v1_namespace_spec import V1NamespaceSpec
from kubernetes.client.models.v1_namespace_status import V1NamespaceStatus
from kubernetes.client.models.v1_security_context import V1SecurityContext
from kubernetes.client.models.v1_host_path_volume_source import V1HostPathVolumeSource
from kubernetes.client.models.v1_rbd_persistent_volume_source import V1RBDPersistentVolumeSource
from kubernetes.client.models.v1_secret_reference import V1SecretReference
from kubernetes.client.models.v1_host_path_volume_source import V1HostPathVolumeSource
from kubernetes.client.models.v1_persistent_volume_claim_volume_source import V1PersistentVolumeClaimVolumeSource
from kubernetes.client.models.v1_persistent_volume_status import V1PersistentVolumeStatus

class MyEncoder(json.JSONEncoder):
    def default(self, obj):  
        
        if isinstance(obj, datetime):  
            return obj.strftime('%Y-%m-%d %H:%M:%S')  
        elif isinstance(obj, date):  
            return obj.strftime("%Y-%m-%d")  
        elif isinstance(obj, V1LabelSelectorRequirement):  
            return {
                "key": obj.key,
                "operator": obj.operator,
                "values": obj.values,
            }
        elif isinstance(obj, V1RBDPersistentVolumeSource):  
            return {
                "fs_type": obj.fs_type,
                "image": obj.image,
                "keyring": obj.keyring,
                "monitors": obj.monitors,
                "pool": obj.pool,
                "read_only": obj.read_only,
                "secret_ref": obj.secret_ref,
                "user": obj.user,
            }
        elif isinstance(obj, V1SecretReference):  
            return {
                "_name": obj._name,
                "namespace": obj.namespace,
            }
        elif isinstance(obj, V1PersistentVolumeStatus):  
            return {
                "message": obj.message,
                "phase": obj.phase,
                "reason": obj.reason,
            }
        elif isinstance(obj, V1PersistentVolumeClaimVolumeSource):  
            return {
                "claim_name": obj.claim_name,
                "read_only": obj.read_only,
            }
        elif isinstance(obj, V1HostPathVolumeSource):  
            return {
                "path": obj.path,
                "type": obj.type,
            }
        elif isinstance(obj, V1SecurityContext):  
            return {
                "privileged": obj.privileged,
                "run_as_group": obj.run_as_group,
                "run_as_user": obj.run_as_user,
            }
        elif isinstance(obj, V1Namespace):  
            return {
                "api_version": obj.api_version,
                "kind": obj.kind,
                "metadata": obj.metadata,
                "spec": obj.spec,
                "status": obj.status
            }
        elif isinstance(obj, V1NamespaceSpec):  
            return {
                "finalizers": obj.finalizers,
            }
        elif isinstance(obj, V1NamespaceStatus):  
            return {
                "phase": obj.phase
            }
        elif isinstance(obj,V1PodTemplateSpec):
            return {
                "metadata": obj.metadata,
                "spec": obj.spec,
            } 
        elif isinstance(obj,V1LabelSelector):
            if  obj.match_expressions:
                return { "match_expressions": obj.match_expressions,} 
            else:       
                return { "match_labels": obj.match_labels,} 
        elif isinstance(obj,V1WeightedPodAffinityTerm):
            return {
                "pod_affinity_term": obj.pod_affinity_term,
                "weight": obj.weight,
            } 
        elif isinstance(obj,V1PodAffinityTerm):
            return {
                "label_selector": obj.label_selector,
                "namespaces": obj.namespaces,
                "topology_key": obj.topology_key,
            } 
        elif isinstance(obj,V1PodAntiAffinity):
            if obj.preferred_during_scheduling_ignored_during_execution:
                return {
                    "preferred_during_scheduling_ignored_during_execution": obj.preferred_during_scheduling_ignored_during_execution,
                }            
            else:     
                return {
                    "required_during_scheduling_ignored_during_execution": obj.required_during_scheduling_ignored_during_execution,
                } 
        elif isinstance(obj,V1PreferredSchedulingTerm):
            return {
                "preference": obj.preference,
                "weight": obj.weight,
            } 
        
        elif isinstance(obj,V1ConfigMapKeySelector):
            return {
                "name": obj.name,
                "optional": obj.optional,
            } 
        elif isinstance(obj,V1PodTemplateSpec):
            return {
                "api_version": obj.api_version,
                "items": obj.items,
                "kind": obj.kind,
                "metadata": obj.metadata,
            }       
            
        elif isinstance(obj,V1EmptyDirVolumeSource):
            return {
                # "medium": obj.medium,
                # "size_limit": obj.size_limit,
            }    
        elif isinstance(obj,V1Volume):
            return {
                "name": obj.name,
                "nfs":obj.nfs,
                "cephfs":obj.cephfs,
                "empty_dir": obj.empty_dir,
                "host_path": obj.host_path,
                "persistent_volume_claim": obj.persistent_volume_claim,
            }      
        elif isinstance(obj,V1PodSpec):
            return {
                "affinity": obj.affinity,
                "containers": obj.containers,
                # "host_network": obj.host_network,
                "image_pull_secrets": obj.image_pull_secrets,
                "node_selector": obj.node_selector,
                "service_account_name": obj.service_account_name,
                "tolerations": obj.tolerations,
                "volumes": obj.volumes,
            }    
            
            
            
        elif isinstance(obj,V1Deployment):
            return {
                "api_version": obj.api_version,
                "kind": obj.kind,
                "metadata": obj.metadata,
                "spec": obj.spec,
                # "status": obj.status,
            }         
            
        elif isinstance(obj,V1DeploymentSpec):
            return {
                "min_ready_seconds": obj.min_ready_seconds,
                # "paused": obj.paused,
                "replicas": obj.replicas,
                "revision_history_limit": obj.revision_history_limit,
                "selector": obj.selector,
                "strategy": obj.strategy,
                "template": obj.template,
            }     
        
        elif isinstance(obj,ExtensionsV1beta1IngressTLS):
            return {
                "hosts": obj.hosts,
                "secret_name": obj.secret_name,
            }
            
        elif isinstance(obj,V1ObjectMeta):
            if obj.name:
                return {
                    # "annotations": obj.annotations,
                    # "cluster_name": obj.cluster_name,
                    # "creation_timestamp": obj.creation_timestamp,
                    "labels": obj.labels,
                    "name": obj.name,
                    "namespace": obj.namespace,
                }     
            else:
                return {
                    "labels": obj.labels,
                }     
            
            
        elif isinstance(obj,V1Taint):
            return {
                "effect": obj.effect,
                "key": obj.key,
                "value": obj._value ,
            }
        elif isinstance(obj,V1NodeSystemInfo):
            return {
                "architecture": obj.architecture,
                "docker_version": obj.container_runtime_version,
                "kernel_version": obj.kernel_version ,
                "kube_proxy_version": obj.kube_proxy_version,
                "operating_system": obj.operating_system,
                "os_image": obj.os_image ,
            }
        elif isinstance(obj,V1LabelSelector):
            return {
                "_match_labels": obj._match_labels,
            }
        # {'rolling_update': {'max_surge': '25%', 'max_unavailable': '25%'},
        # 'type': 'RollingUpdate'}
        elif isinstance(obj,V1DeploymentStrategy):
            return {
                "rolling_update": obj.rolling_update,
                "type": obj.type,
            }    
        elif isinstance(obj,V1RollingUpdateDeployment):
            return {
                "max_surge": obj.max_surge,
                "max_unavailable": obj.max_unavailable,
            }  
        elif isinstance(obj,V1LocalObjectReference):
            return {
                "name": obj.name,
            }    
        elif isinstance(obj,V1Container):
            return {
                "image": obj.image,
                "image_pull_policy": obj.image_pull_policy,
                "args":obj.args,
                "command":obj.command,
                "name":obj.name,
                "lifecycle":obj.lifecycle,
                "working_dir":obj.working_dir,
                "ports": obj.ports,
                "env": obj.env,
                "env_from": obj.env_from,
                "readiness_probe": obj.readiness_probe,
                "liveness_probe": obj.liveness_probe,
                "resources": obj.resources,
                "volume_mounts": obj.volume_mounts,
                "security_context": obj.security_context,
            }    
        elif isinstance(obj,V1ContainerPort):
            return {
                "container_port": obj.container_port,
                # "host_ip": obj.host_ip,
                # "host_port": obj.host_port,
                "name": obj.name,
                "protocol": obj.protocol,
            }   
        elif isinstance(obj,V1ServicePort):
            return {
                "name": obj.name,
                "node_port": obj.node_port,
                "port": obj.port,
                "protocol": obj.protocol,
                "target_port": obj.target_port,
            }   
        elif isinstance(obj,V1ServiceStatus):
            return {
                "load_balancer": obj.load_balancer,
            }   
        elif isinstance(obj,V1VolumeMount):
            return {
                "mount_path": obj.mount_path,
                "name": obj.name,
                "read_only": obj.read_only,
                "sub_path": obj.sub_path,
            }  
        elif isinstance(obj,V1EnvVar):
            if obj.value:
                return {
                    "name": obj.name,
                    "value": obj.value,
                }
            else:
                return {
                    "name": obj.name,
                    "value_from": obj.value_from ,                
                }

        elif isinstance(obj,V1EnvVarSource):
            if obj.secret_key_ref:
                return {
                    "secret_key_ref": obj.secret_key_ref , 
                }
            elif obj.config_map_key_ref:
                return {
                    "config_map_key_ref": obj.config_map_key_ref,  
                }
            elif obj.field_ref:
                return {
                    "field_ref": obj.field_ref,
                }
            else:
                return {
                    "resource_field_ref": obj.resource_field_ref ,
                }
        elif isinstance(obj,V1SecretKeySelector):
            return {
                "key": obj.key,
                "name": obj.name,
            }
        elif isinstance(obj,V1Probe):
            return {
                    "httpGet": obj.http_get,
                    "tcpSocket": obj.tcp_socket,
                    "initialDelaySeconds": obj.initial_delay_seconds,
                    "periodSeconds": obj.period_seconds,
                    "failureThreshold": obj.failure_threshold,
                    "timeoutSeconds": obj.timeout_seconds,                
            }
            # if obj.tcp_socket:
            #     return {
            #         "tcpSocket": obj.tcp_socket,
            #         "initialDelaySeconds": obj.initial_delay_seconds,
            #         "periodSeconds": obj.period_seconds,
            #         "failureThreshold": obj.failure_threshold,
            #         "timeoutSeconds": obj.timeout_seconds,
            #     }      
            # elif obj.http_get:
            #     return {
            #         "httpGet": obj.http_get,
            #         "initialDelaySeconds": obj.initial_delay_seconds,
            #         "periodSeconds": obj.period_seconds,
            #         "failureThreshold": obj.failure_threshold,
            #         "timeoutSeconds": obj.timeout_seconds,
            #     }      
            # elif obj._exec:
            #     return {
            #         "exec": obj._exec,
            #         "initialDelaySeconds": obj.initial_delay_seconds,
            #         "periodSeconds": obj.period_seconds,
            #         "failureThreshold": obj.failure_threshold,
            #         "timeoutSeconds": obj.timeout_seconds,
            #     }      
            # else:
            #     pass   
        elif isinstance(obj,V1TCPSocketAction):
            return {
                # "host": obj.host,
                "port": obj.port,
            }   
        elif isinstance(obj,V1HTTPGetAction):
            return {
                # "host": obj.host,
                # "http_headers": obj.http_headers,
                "path": obj.path,
                "port": obj.port,
                # "scheme": obj.scheme,
            }     
        elif isinstance(obj,V1Affinity):
            return {
                "node_affinity": obj.node_affinity,
                "pod_affinity": obj.pod_affinity,
                "pod_anti_affinity": obj.pod_anti_affinity,
            } 
        elif isinstance(obj,V1NodeAffinity):
            if  obj.preferred_during_scheduling_ignored_during_execution:
                return {
                    "preferred_during_scheduling_ignored_during_execution": obj.preferred_during_scheduling_ignored_during_execution,
                }
            else:                
                return {
                    "required_during_scheduling_ignored_during_execution": obj.required_during_scheduling_ignored_during_execution,
                }  
        elif isinstance(obj,V1NodeSelector):
            return {
                "node_selector_terms": obj.node_selector_terms,
            }        
        elif isinstance(obj,V1NodeSelectorTerm):
            return {
                "match_expressions": obj.match_expressions,
                "match_fields": obj.match_fields,
            }     
        elif isinstance(obj,V1NodeSelectorRequirement):
            return {
                "key": obj.key,
                "operator": obj.operator,
                "values": obj.values,
            }   
        elif isinstance(obj,V1ObjectFieldSelector):
            return {
                "api_version": obj.api_version,
                "field_path": obj.field_path,
            }   
        elif isinstance(obj,V1Toleration):
            return {
                "effect": obj.effect,
                "key": obj.key,
                "operator": obj.operator,
                "toleration_seconds": obj.toleration_seconds,
                "value": obj._value ,
            }  
        elif isinstance(obj,V1NFSVolumeSource):
            return {
                "path": obj.path,
                "read_only": obj.read_only,
                "server": obj.server ,
            }
        elif isinstance(obj,V1ObjectReference):
            return {
                "api_version": obj.api_version,
                "field_path": obj.field_path,
                "kind": obj.kind ,
                "name": obj.name,
                "namespace": obj.namespace,
            }          
        elif isinstance(obj,V1PersistentVolumeClaimStatus):
            return {
                "access_modes": obj.access_modes[0],
                "capacity": obj.capacity['storage'],
                "phase": obj.phase ,
            }   
        elif isinstance(obj,V1ResourceRequirements):
            return {
                "limits": obj.limits,
                "requests": obj.requests,
            }  
        elif isinstance(obj,V1LoadBalancerStatus):
            return {
                "ingress": obj.ingress,
            }     
        elif isinstance(obj,V1PodSecurityContext):
            return {
                "fs_group": obj.fs_group,
                "run_as_group": obj.run_as_group,
                "run_as_non_root": obj.run_as_non_root ,
                "run_as_user": obj.run_as_user,
                "se_linux_options": obj.se_linux_options,
            }      
        elif isinstance(obj,ExtensionsV1beta1IngressRule):
            return {
                "host": obj.host,
                "http": obj.http,
            }  
        elif isinstance(obj,ExtensionsV1beta1HTTPIngressRuleValue):
            return {
                "paths": obj.paths,
            }    
        elif isinstance(obj,ExtensionsV1beta1HTTPIngressPath):
            return {
                "path": obj.path,
                "backend": obj.backend,
            }            
        elif isinstance(obj,ExtensionsV1beta1IngressBackend):
            return {
                "service_name": obj.service_name,
                "service_port": obj.service_port,
            }    
   
        else:  
            return json.JSONEncoder.default(self, obj)
        
        
class DateEncoder(json.JSONEncoder):
    def default(self, obj):  
        if isinstance(obj, datetime):  
            return obj.strftime('%Y-%m-%d %H:%M:%S')  
        elif isinstance(obj, date):  
            return obj.strftime("%Y-%m-%d")     
        else:  
            return json.JSONEncoder.default(self, obj)
    
    

















# #格式化字典数组(ports专用)
# def format_obj_list(obj_list):
#     results = ""

#     for obj in obj_list:
#         name = obj.name
#         node_port = obj.node_port
#         port = obj.port 
#         protocol = obj.protocol 
#         target_port = obj.target_port
        
#         tmp = "[name:{}\nnode_port:{}\nport:{}\nprotocol:{}\ntarget_port:{}\n]".\
#                 format(name,node_port,port,protocol,target_port)
        
#         # print(tmp)
#         results = results +"\n\n" +tmp
#     # print(results)
#     return results

# def format_pod_port_list(obj_list):
#     results = ""

#     for obj in obj_list:
#         name = obj.name
#         # node_port = obj.node_port
#         container_port = obj.container_port 
#         protocol = obj.protocol 
#         host_ip = obj.host_ip
#         host_port = obj.host_port
#         tmp = "[name:{}\ncontainer_port:{}\nhost_ip:{}\nprotocol:{}\nhost_port:{}\n]".\
#                 format(name,container_port,host_ip,protocol,host_port)
        
#         # print(tmp)
#         results = results +"\n\n" +tmp
#     # print(results)
#     return results

# def convert_to_dicts(objs):
#     print(type(objs))
#     '''把对象列表转换为字典列表'''
#     obj_arr = []
#     for o in objs:
#         #把Object对象转换成Dict对象
#         dict = {}
#         dict.update(o.__dict__)
#         obj_arr.append(dict)
#     return obj_arr

# #格式化字典
# def format_dict(dict_obj):
#     if dict_obj == None:
#         return ""
#     else:
#         s  = ""
#         for k,v in dict_obj.items():
#             t  = "{}:{}\n".format(k,v)
#             s = s+t
#         return s