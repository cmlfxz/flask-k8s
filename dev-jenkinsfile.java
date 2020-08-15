pipeline {
    agent any
    parameters {
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
    }
    environment {
        TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
        ENV='dev'
        HARBOR_REGISTRY = 'myhub.mydocker.com'
        CLI="/usr/bin/kubectl --kubeconfig /root/.kube/config"
    }
    // 必须包含此步骤
    stages {
        stage('display var') {
            steps {
                echo "Runing ${env.BUILD_ID}"
                echo "BRANCH ${params.BRANCH}"
                echo "tag: $TAG  replicas: ${params.REPLICAS} "
            }
        }
        stage('checkout') {
            steps {
                script {
                    // revision = params.BRANCH
                    revision = 'develop'
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
            steps {
                echo  "$TAG, $ENV" 
                withCredentials([usernamePassword(credentialsId: 'dev-dockerHub', passwordVariable: 'dockerHubPassword', usernameVariable: 'dockerHubUser')]){
                    sh '''
                        sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
                        cd $WORKSPACE/k8s/
                        docker login -u ${dockerHubUser} -p ${dockerHubPassword} $HARBOR_REGISTRY
                    '''
                }

            }
        }
        stage('deploy dev'){
            steps {
                withCredentials([usernamePassword(credentialsId: 'dev-dockerHub', passwordVariable: 'dockerHubPassword', usernameVariable: 'dockerHubUser')]){
                    sh '''
                        namespace="$PROJECT-$ENV"
                        $CLI create secret docker-registry harborsecret --docker-server=$harbor_registry --docker-username=$harbor_user \
                            --docker-password=$harbor_pass --docker-email=$harbor_email --namespace=$namespace 
                        cd $WORKSPACE/k8s/
                        sh  build.sh --action=deploy --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS --harbor_registry=$HARBOR_REGISTRY 
                    '''
                }

            }
        }

    }

}