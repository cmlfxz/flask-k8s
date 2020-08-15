pipeline {
    agent any
    parameters {
        choice(
            description: '发布还是回滚，生产才有回滚操作',
            name: 'ACTION',
            choices: ['deploy','rollout']
        )
        string(
            description: '项目',
            name: 'PROJECT',
            defaultValue: "ms"
        )
        choice(
            description: '你需要选择哪个模块进行构建 ?',
            name: 'SERVICE',
            choices: ['flask-k8s']
        )
        string (
            name: 'URL',
            defaultValue: 'https://gitee.com/cmlfxz/flask-k8s.git',
            description: 'git url'
        )

        string(
            description: '副本数',
            name: 'REPLICAS',
            defaultValue: "1"
        )

        choice(
            description: '正式环境发布类型 ?',
            name: 'TYPE',
            choices: ['canary', 'ab']
        )
        choice(
            description: '正式环境灰度值',
            name: 'CANARY_WEIGHT',
            choices: ['10','20','30','40','50','60','70','80','90','100']
        )
    }
    environment {
        TAG= sh(returnStdout: true,script: 'git describe --tags `git rev-list --tags --max-count=1`')
        ENV='prod'
        // 正式对应修改
        HARBOR_REGISTRY = 'myhub.mydocker.com'
        CLI="/usr/bin/kubectl --kubeconfig /root/.kube/config"
    }
    // 必须包含此步骤
    stages {
        stage('display var') {
            steps {
                echo "Runing ${env.BUILD_ID}"
                echo "BRANCH ${params.BRANCH}"
                echo "tag: $TAG  replicas: ${params.REPLICAS} harbor: ${HARBOR_REGISTRY}"
            }
        }
        stage('checkout') {
            steps {
                script {
                    revision = env.TAG
                }
                checkout([
                    $class: 'GitSCM', 
                    branches: [[name: "${revision}"]], 
                    doGenerateSubmoduleConfigurations: false, 
                    extensions: [],
                    submoduleCfg: [], 
                    userRemoteConfigs: [[
                        credentialsId: '7c6a16ea-308d-47aa-9d95-6487cc215c03',
                        url: "${params.URL}" ]]
                ])
            }
        }

        stage('build') {
            when {
                expression { return params.ACTION == "deploy" }
            }
            steps {
                echo  "$TAG, $ENV" 
                withCredentials([usernamePassword(credentialsId: 'prod-dockerHub', passwordVariable: 'dockerHubPassword', usernameVariable: 'dockerHubUser')]){
                    sh '''
                        docker login -u ${dockerHubUser} -p ${dockerHubPassword} $HARBOR_REGISTRY
                        cd $WORKSPACE/k8s/
                        sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
                    '''
                }

            }
        }

        stage('deploy prod'){
            when {
                allOf {
                    environment name: 'ACTION', value: 'deploy'
                }
            }
            steps {
                 echo "$TYPE $CANARY_WEIGHT"
                withCredentials([usernamePassword(credentialsId: 'prod-dockerHub', passwordVariable: 'dockerHubPassword', usernameVariable: 'dockerHubUser')]){
                    sh '''
                        namespace="$PROJECT-$ENV"
                        $CLI create secret docker-registry harborsecret --docker-server=$harbor_registry --docker-username=$harbor_user \
                            --docker-password=$harbor_pass --docker-email=$harbor_email --namespace=$namespace 
                        cd $WORKSPACE/k8s/
                        sh  build.sh --action=deploy --env=prod --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS  --type=$TYPE --canary_weight=$CANARY_WEIGHT --harbor_registry=$HARBOR_REGISTRY 
                    '''
                }

            }
        }
        stage('rollout'){
            when {
                allOf {
                    environment name: 'ACTION', value: 'rollout';
                }
            }
            steps {
                //  bug build.sh检查rollout存不存在需要用到tag
                 sh '''
                    cd $WORKSPACE/k8s/
                    sh  build.sh --action=rollout --env=$ENV --project=$PROJECT  --tag=$TAG
                '''
            }
        }
    }

}