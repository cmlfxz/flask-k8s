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
        // gitParameter (
        //     name: 'BRANCH', 
        //     branchFilter: 'origin/(.*)', 
        //     defaultValue: 'develop', 
        //     type: 'PT_BRANCH',
        //     description:"git branch choice"
        // )
        string(
            description: '副本数',
            name: 'REPLICAS',
            defaultValue: "1"
        )
    }
    // environment {
    //     ENV = 'dev'
    //     PROJECT = 'ms'
    //     SERVICE = 'flask-k8s'
    //     HARBOR_REGISTRY = 'myhub.mydocker.com'
    //     ACTION = params.ACTION
    //     用这个作为dev的tag 最新的commit id
    //     TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
    // }
    // 必须包含此步骤
    stages {
        stage('set TAG & ENV & harbor_registry'){
            steps {
                script {
                        env.TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
                        env.ENV='dev'
                        env.HARBOR_REGISTRY = 'myhub.mydocker.com'
                }

            }
        }
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
                sh '''
                    cd $WORKSPACE/k8s/
                    sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
                '''
            }
        }
        stage('deploy dev'){
            steps {
                 sh '''
                    cd $WORKSPACE/k8s/
                    sh  build.sh --action=deploy --env=dev --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS --harbor_registry=$HARBOR_REGISTRY 
                '''
            }
        }

    }

}