#!/bin/bash
rm -rf flask-k8s

git clone https://cmlfxz:dugu16829987@gitee.com/cmlfxz/flask-k8s.git
#git checkout release-0.2
#git rev-parse --short HEAD

canary_weight=0
input_canary() {
    for i in $(seq 1 5)
    do
        read -p "请输入灰度数值(10.20..100):" number

        #判断输入是不是数字,命令结果为1 为数字,为0 不是数字
        echo $number | grep -q '[^0-9]'
        if [[ $? -eq 1 ]] &&  [[ "$number" -le 100 ]]; then
            canary_weight=$number
            break
        else
            echo "你输入的$canary_weight不是小于等于100的数字，5次机会,重新输入!"
        fi
    done
    echo "$canary_weight"
}

if [ "$1" == "dev" ];then
    cd flask-k8s
    git checkout develop
    cd k8s
    commit=$(git rev-parse --short HEAD)
    echo "$commit"
    # 变量 环境 项目 服务名  副本数 仓库地址 (tag)
    sh  build.sh --action=build --env=dev --project=ms --service=flask-k8s --tag=$commit 
    if [ "$?" -ne 0 ];then
        echo "build 失败" && exit 1
    fi
    sh  build.sh --action=deploy --env=dev --project=ms --service=flask-k8s --tag=$commit --replicas=1
elif [ "$1" == "prod" ];then
    cd flask-k8s
    if [ ! -z "$2" ];then
      tag=$2
    else
      git fetch --tags
      tag=$(git describe --tags `git rev-list --tags --max-count=1`)
    fi
    echo "$tag"
    git checkout $tag
    cd k8s
    sh  build.sh --action=build --env=prod --project=ms --service=flask-k8s --tag=$tag
    if [ "$?" -ne 0 ];then
      echo "build 失败" && exit 1
    fi
    #输入发布类型，如果是canary发布，还得输入灰度值
    read -p "请输入发布模式(ab|canary|rollout)大小写敏感:" type
    case $type in
      ab | AB)
        type=ab
        ;;
      canary | CANARY |gray |GRAY)
        type=canary
        input_canary
        ;;
      roll|rollout|ROLLOUT)
        type=rollout
        ;;
      *)
        echo "没有$type这种发布模式" && exit 1
        ;;
    sh -x   build.sh --action=deploy --env=prod  --project=ms --service=flask-k8s --tag=$tag --replicas=1 --type=$type --canary_weight=$canary_weight
fi
