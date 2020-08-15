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
        CLI="/usr/bin/kubectl --kubeconfig /root/.kube/config"

        HARBOR_REGISTRY = 'myhub.mydocker.com'
        HARBOR_EMAIL = '915613275@qq.com'
        // docker账号密码的保存在jenkins的Cred ID
        DOCKER_HUB_ID='dev-dockerHub'
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
                withCredentials([usernamePassword(credentialsId: "$DOCKER_HUB_ID", passwordVariable: 'dockerHubPassword', usernameVariable: 'dockerHubUser')]){
                    sh '''
                        docker login -u ${dockerHubUser} -p ${dockerHubPassword} $HARBOR_REGISTRY
                        cd $WORKSPACE/k8s/
                        sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
                    '''
                }

            }
        }
        stage('deploy dev'){
            steps {
                withCredentials([usernamePassword(credentialsId: "$DOCKER_HUB_ID", passwordVariable: 'dockerHubPassword', usernameVariable: 'dockerHubUser')]){
                    configFileProvider([configFile(fileId: 'dev-k8s-config', targetLocation: '/root/.kube/config')]) {
                        sh '''
                            namespace="$PROJECT-$ENV"
                            $CLI create secret docker-registry harborsecret --docker-server=$HARBOR_REGISTRY --docker-username=$dockerHubUser \
                                --docker-password=$dockerHubPassword --docker-email=$HARBOR_EMAIL --namespace=$namespace || true
                        '''
                    }
                    sh  '''
                        cd $WORKSPACE/k8s/
                        sh  build.sh --action=deploy --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS --harbor_registry=$HARBOR_REGISTRY 
                    '''
                }

            }
        }

    }

    post {
        // success {
        //     emailext (
        //         subject: "SUCCESSFUL: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
        //         body: """<p>SUCCESSFUL: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]':</p>
        //             <p>Check console output at "<a href="${env.BUILD_URL}">${env.JOB_NAME} [${env.BUILD_NUMBER}]</a>"</p>""",
        //         to: "18688376362@163.com",
        //         from: "18688376362@163.com"
        //     )
        // }
        // failure {
        //     emailext (
        //         subject: "FAILED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'",
        //         body: """<p>FAILED: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]':</p>
        //             <p>Check console output at "<a href="${env.BUILD_URL}">${env.JOB_NAME} [${env.BUILD_NUMBER}]</a>"</p>""",
        //         to: "18688376362@163.com",
        //         from: "18688376362@163.com"
        //     )
        // }
        success {
            //当此Pipeline成功时打印消息
            echo 'success'
            dingTalk (
                robot: '4def1f0b-4f7c-4793-b1d0-6f5394afa257',
                type: 'LINK',
                messageUrl:'https://oapi.dingtalk.com/robot/send?access_token=bba613c1e866e921d3075c21c8eda6aac020d6a7f679974645ddd05cb33a59e8', 
                text:["更新记录"],
                picUrl:'', 
                // jenkinsUrl:'http://http://192.168.11.142:8080/jenkins/', 
                title:'构建成功', 
                // notifyPeople:'Administrator'
            )
        }
        // failure {
        //     //当此Pipeline失败时打印消息
        //     echo 'failure'
        //     dingTalk (
        //         messageUrl:'bba613c1e866e921d3075c21c8eda6aac020d6a7f679974645ddd05cb33a59e8', 
        //         imageUrl:'', jenkinsUrl:'http://http://192.168.11.142:8080/jenkins/', 
        //         message:'构建失败', 
        //         notifyPeople:'Administrator'
        //     )
        // }
        aborted {
            //当此Pipeline 终止时打印消息
            echo 'aborted'  
        }
    }

}