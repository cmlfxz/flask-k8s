#!/bin/bash
#需要手动更改：部分命名，环境(dev,prod,stage),版本
namespace=ms-dev
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$namespace/${namespace}/"


service=flask-k8s
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$service/${service}/"

harbor_registry=myhub.mydocker.com
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$harbor_registry/${harbor_registry}/"

port=8082
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$port/${port}/"

/bin/mv demo-vs.yaml   ${service}-vs.yaml
/bin/mv demo-dr.yaml   ${service}-dr.yaml
