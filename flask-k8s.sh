#!/bin/bash
rm -rf flask-k8s

git clone https://cmlfxz:dugu16829987@gitee.com/cmlfxz/flask-k8s.git
#git checkout release-0.2
#git rev-parse --short HEAD


if [ "$1" == "dev" ];then
        cd flask-k8s
        git checkout develop
        cd k8s
        commit=$(git rev-parse --short HEAD)
        echo "$commit"
        # 变量 环境 项目 服务名  副本数 仓库地址 (tag)
        sh  build.sh build dev ms flask-k8s $commit
        if [ "$?" -ne 0 ];then
          echo "build 失败" && exit 1
        fi
        sh  build.sh deploy dev ms flask-k8s $commit 1
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
        sh  build.sh build $1 ms flask-k8s $tag
        if [ "$?" -ne 0 ];then
          echo "build 失败" && exit 1
        fi
        sh -x   build.sh deploy $1  ms flask-k8s $tag
fi
