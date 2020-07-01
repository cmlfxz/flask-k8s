#!/bin/bash

if [ "$#" -lt 5 ];then
  echo "参数不对"
  echo "Usage: docker_build.sh 动作(build/deploy/gray) 环境(dev,stage,prod) 项目名 服务名(product) tag(0.6) 副本数"
  exit
fi

if [ `echo "$1" |egrep -i "build|deploy|gray" |wc -l` -eq 0  ];then
  echo "第一个参数必须为build deploy"
  exit
fi
if [ `echo "$2" |egrep -i "dev|stage|release|prod" |wc -l` -eq 0  ];then
  echo "第二个参数必须为部署环境dev release(stage) prod"
  exit
fi


env=$2
harbor_registry=hyfjhxz5.mirror.aliyuncs.com
if [ `echo "$env" |egrep -i "dev" |wc -l` -eq 1  ];then
  env=dev
  harbor_registry=myhub.mydocker.com
elif [ `echo "$env" |egrep -i "stage|staging|release|pre" |wc -l` -eq 1  ];then
  env=release
  harbor_registry=myhub.mydocker.com
elif [ `echo "$env" |egrep -i "prod|master" |wc -l` -eq 1   ];then 
  env=prod
  harbor_registry=myhub.mydocker.com
fi
#命名空间为项目名-环境
namespace=$3-$env
service=$4
tag=$5
replicas=$6
if [ -z "$replicas" ];then
  replicas=1
  echo "副本数没设置，默认为1"
fi
workdir=$(dirname $PWD)

harbor_user="cmlfxz"
harbor_pass="DUgu16829987"
harbor_email="915613275@qq.com"
#cd $workdir
#mvn clean package -DskipTests

build() {
   if [ -z "${harbor_registry}" ];then
      echo "$harbor_registey 没设置harbor地址"
      exit
   fi
   echo "当前正在构建$env环境"
   cd $workdir/
   #service=${service%-*}
   image_name=$harbor_registry/$namespace/${service}:$tag
   docker build -t ${image_name} .
   docker login -u $harbor_user -p $harbor_pass $harbor_registry
   docker push ${image_name} 
}

deploy(){
  #service=${service%-*}
  if [ "$env" == "dev" ];then
    echo "当前正在部署开发环境"
    cd $workdir/k8s/$env
    kubectl create namespace $namespace
    kubectl label namespace $namespace istio-injection=enabled
    kubectl create secret docker-registry harborsecret --docker-server=$harbor_registry --docker-username=$harbor_user\
               --docker-password=$harbor_pass --docker-email=$harbor_email --namespace=$namespace
    kustomize edit set image $harbor_registry/$namespace/$service=$harbor_registry/$namespace/${service}:$tag
    kustomize edit set namespace $namespace
    kustomize edit set replicas $service=$replicas
    kustomize build .
    kustomize build . |kubectl apply -f -
    kubectl get pod,svc,vs,dr,gateway -n $namespace
  elif [ "$env" == "release"  ];then
    echo "当前正在部署预发布环境"
    cd $workdir/k8s/$env
    kubectl create namespace $namespace
    kubectl label namespace $namespace istio-injection=enabled
    kubectl create secret docker-registry harborsecret --docker-server=$harbor_registry --docker-username=$harbor_user\
             --docker-password=$harbor_pass --docker-email=$harbor_email --namespace=$namespace
    kustomize edit set image $harbor_registry/$namespace/$service=$harbor_registry/$namespace/${service}:$tag
    kustomize edit set namespace $namespace
    kustomize build .
    kustomize build . |kubectl apply -f -
    kubectl get pod,svc,vs,dr,gateway -n $namespace
  elif [ "$env" == "prod" ];then
    echo "当前正在部署生产环境,生产环境yaml保存在各自版本的目录下"
    #根据用户输入进入ab还是灰度

    read -p "请输入发布模式(ab|canary|rollout):" type
    if [ `echo "$type" |egrep -i "ab|canary" |wc -l` -eq 1 ];then

      cd $workdir/k8s/$env/$tag/$type

      if [ `echo "$type" |egrep -i "canary" |wc -l` -eq 1 ];then
        echo "正在执行灰度发布,先输入灰度值，生成灰度文件"
        ######输入灰度值######
        for i in $(seq 1 5)
        do
          read -p "请输入灰度数值(10.20..100):" canary_weight
          #判断输入是不是数字,命令结果为1 为数字,为0 不是数字
          echo $canary_weight | grep -q '[^0-9]'
          if [[ $? -eq 1 ]] &&  [[ "$canary_weight" -le 100 ]]; then
            prod_weight=$(( 100 -$canary_weight))
            break
          else
            echo "你输入的$canary_weight不是小于等于100的数字，5次机会,重新输入!"
          fi 
        done
        ############
        echo "$canary_weight $prod_weight"
        ###########
        if [ -f "$service-vs.yaml" ];then
          sed -i  "s/\$canary_weight/$canary_weight/g"  $service-vs.yaml
          sed -i  "s/\$prod_weight/$prod_weight/g"  $service-vs.yaml
        else
          echo "灰度文件$service-vs.yaml 不存在,请检查"
          exit 1
        fi
        #同时作为外部服务的service才需要加上这个
        if [ -f "$namespace-gateway.yaml" ];then
          sed -i  "s/\$canary_weight/$canary_weight/g"  $namespace-gateway.yaml
          sed -i  "s/\$prod_weight/$prod_weight/g"  $namespace-gateway.yaml
        else
          echo "灰度文件$namespace-gateway.yaml 不存在,请检查"
          # exit 1
        fi
      fi
      ########################
      echo "发布deployment,svc"
      cd $workdir/k8s/$env/$tag
      kubectl create namespace $namespace
      kubectl label namespace $namespace istio-injection=enabled
      kubectl create secret docker-registry harborsecret --docker-server=$harbor_registry --docker-username=$harbor_user\
            --docker-password=$harbor_pass --docker-email=$harbor_email --namespace=$namespace
      kustomize edit set image $harbor_registry/$namespace/$service=$harbor_registry/$namespace/${service}:$tag
      kustomize edit set namespace $namespace
      kustomize build . &&  kustomize build . |kubectl apply -f -
      
      ########################
      echo "发布$type部分"
      cd $workdir/k8s/$env/$tag/$type
      kustomize edit set namespace $namespace
      kustomize build . &&  kustomize build . |kubectl apply -f -
      kubectl get pod,svc,vs,dr,gateway -n $namespace
      #######################
      
    elif [ `echo "$type" |egrep -i "rollout" |wc -l` -eq 1 ];then
      echo "你正在执行$env环境回滚操作"
      rollout_dir = "$workdir/k8s/$env/$tag/$type"
      if [ ! -d "$rollout_dir"];then
        echo "没有$rollout_dir回滚目录，请检查" && exit 1
      fi
      cd $rollout_dir
      kustomize edit set namespace $namespace
      kustomize build . &&  kustomize build . |kubectl apply -f -
      kubectl get pod,svc,vs,dr,gateway -n $namespace
    else
      echo "没有$type这种发布模式" && exit 1
    fi

  fi
}

$1
