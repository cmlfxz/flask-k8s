#!/bin/bash
COMMANDLINE="$*"
action=""
env=""
project=""
service=""
tag=""
replicas=""
harbor_registry=""
type=""
canary_weight=""

for COMMAND in $COMMANDLINE
do
    key=$(echo $COMMAND | awk -F"=" '{print $1}')
    val=$(echo $COMMAND | awk -F"=" '{print $2}')
    # $ENV $PROJECT $SERVICE $TAG
    case $key in
        --action)
            action=$val
        ;;
        --env)
            env=$val
        ;;
        --project)
            project=$val
        ;;
        --service)
            service=$val
        ;;
        --tag)
            tag=$val
        ;;
        --replicas)
            replicas=$val
        ;;
        --harbor_registry)
            harbor_registry=$val
        ;;
        --type)
            type=$val
        ;;
        --canary_weight)
            canary_weight=$val
        ;;
    esac
done
#----------参数处理
echo "$action $env $project $service $tag $replicas $harbor_registry $type $canary_weight"
# if [[ "$action"=="" || "$env"=="" || "$project"==""  || "$service"=="" || "$tag"=="" ]];then
if [ "$#" -lt 5 ];then
    echo "缺少参数"
    echo "Usage sh build.sh --action=build/deploy --env=dev/test/prod --project=ms --service=flask-k8s \
            --tag=commit_id/v1.0 --replicas=1 --harbor_registry=myhub.mydocker.com --type=ab|canary|rollout --canary_weight=10"
    exit 1
fi
if [ -z "$replicas" ];then
  replicas=1
  echo "副本数没设置，默认为1"
fi
if [ -z "$harbor_registry" ];then
  harbor_registry=myhub.mydocker.com
  echo "harbor仓库没设置，默认为myhub.mydocker.com"
fi
namespace=$project-$env
workdir=$(dirname $PWD)

#正式测试保持同一套密码
harbor_user="cmlfxz"
harbor_pass="DUgu16829987"
harbor_email="915613275@qq.com"
CLI="/usr/bin/kubectl --kubeconfig /root/.kube/config"

# prod_weight=100
# canary_weight=0
# input_canary() {
#     for i in $(seq 1 5)
#     do
#         read -p "请输入灰度数值(10.20..100):" number

#         #判断输入是不是数字,命令结果为1 为数字,为0 不是数字
#         echo $number | grep -q '[^0-9]'
#         if [[ $? -eq 1 ]] &&  [[ "$number" -le 100 ]]; then
#             canary_weight=$number
#             prod_weight=$(( 100 -$canary_weight))
#             break
#         else
#             echo "你输入的$canary_weight不是小于等于100的数字，5次机会,重新输入!"
#         fi
#     done
#     echo "$canary_weight $prod_weight"
# }



build() {
   echo "当前正在构建$env环境"
   cd $workdir/
   image_name=$harbor_registry/$namespace/${service}:$tag
   docker build -t ${image_name} .
   docker login -u $harbor_user -p $harbor_pass $harbor_registry
   docker push ${image_name} 
}
common_deploy() {
    $CLI create namespace $namespace
    $CLI label namespace $namespace istio-injection=enabled
    $CLI create secret docker-registry harborsecret --docker-server=$harbor_registry --docker-username=$harbor_user\
               --docker-password=$harbor_pass --docker-email=$harbor_email --namespace=$namespace
    kustomize edit set image $harbor_registry/$namespace/$service=$harbor_registry/$namespace/${service}:$tag
    kustomize edit set namespace $namespace
    #bug 副本数匹配的是deployment的名字，生产版本deployment name是带版本号的
    if [ "$env" = "prod" ];then
        kustomize edit set replicas $service-$tag=$replicas
    else
        kustomize edit set replicas $service=$replicas
    fi
    kustomize build . 
    kustomize build . |$CLI apply -f -
}
deploy_dev() {
    echo "当前正在部署开发环境"
    cd $workdir/k8s/$env
    common_deploy
    $CLI get pod,svc,vs,dr,gateway -n $namespace
}
mod_yaml() {
    prod_weight=$(( 100 -$canary_weight))
     echo "canary_weight: $canary_weight prod_weight:$prod_weight"
    if [ -f "$service-vs.yaml" ];then
        sed -i  "s/\$canary_weight/$canary_weight/g"  $service-vs.yaml
        sed -i  "s/\$prod_weight/$prod_weight/g"  $service-vs.yaml
    else
        echo "灰度文件$service-vs.yaml 不存在,请检查" && exit 1
    fi
    #修改gateway文件，假如存在的话
    if [ -f "$namespace-gateway.yaml" ];then
        sed -i  "s/\$canary_weight/$canary_weight/g"  $namespace-gateway.yaml
        sed -i  "s/\$prod_weight/$prod_weight/g"  $namespace-gateway.yaml
    else
        echo "灰度文件$namespace-gateway.yaml 不存在,请检查"
        # exit 1
    fi  
}

deploy_prod() {
    echo "当前正在部署生产环境"
    # read -p "请输入发布模式(ab|canary|rollout)大小写敏感:" type
    case $type in
        ab|canary)
            cd $workdir/k8s/$env/$tag/$type
            if [ "$type"=='$canary' ];then
                #input_canary
                mod_yaml
            fi
            echo "发布deployment,svc"
            cd $workdir/k8s/$env/$tag
            common_deploy
            echo "发布ab/canary部分"
            ab_canary_deploy
            $CLI get pod,svc,vs,dr,gateway -n $namespace
        ;;
        rollout)
            rollout
        ;;
        *)
            echo "没有$type这种发布模式" && exit 1
        ;;

    esac
}
#执行ab_canary的yaml
ab_canary_deploy(){
    dir="$workdir/k8s/$env/$tag/$type"
    [ ! -d "$dir" ] && echo "没有$dir $type目录，请检查" && exit 1
    cd $dir
    kustomize edit set namespace $namespace
    kustomize build . &&  kustomize build . |$CLI apply -f -
}
rollout(){
    echo "你正在执行$env环境回滚操作"
    dir="$workdir/k8s/$env/$tag/$type"
    [ ! -d "$dir"] && echo "没有$dir回滚目录，请检查" && exit 1
    cd $dir
    kustomize edit set namespace $namespace
    kustomize build . &&  kustomize build . |$CLI apply -f -
}


case $action in
    build)
        build
    ;;
    deploy)
        deploy_$env
    ;;
esac