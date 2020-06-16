#!/bin/bash
#需要手动更改：部分命名，环境(dev,prod,stage),版本
namespace=default
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$namespace/${namespace}/"


service=flask-tutorial
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$service/${service}/"

harbor_registry=myhub.mydocker.com
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$harbor_registry/${harbor_registry}/"

port=8081
find ./* -name "*.y*ml"  |xargs sed -i  "s/\$port/${port}/"


/bin/mv default-gateway.yaml   ${namespace}-gateway.yaml
/bin/mv default-vs.yaml   ${namespace}-vs.yaml
/bin/mv demo-deployment.yaml   ${service}-deployment.yaml
/bin/mv demo-vs.yaml   ${service}-vs.yaml
/bin/mv demo-dr.yaml   ${service}-dr.yaml
