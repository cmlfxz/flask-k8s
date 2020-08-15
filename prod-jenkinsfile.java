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
        // gitParameter (
        //     name: 'BRANCH', 
        //     branchFilter: 'origin/(.*)', 
        //     defaultValue: 'develop', 
        //     type: 'PT_BRANCH',
        //     description:"git branch choice"
        // )
        // gitParameter (
        //     type: 'PT_TAG',
        //     defaultValue: '0.1',
        //     name: 'TAG', 
        //     description:"git tag choice"
        // )

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
        // 正式应该是阿里云
        HARBOR_REGISTRY = 'myhub.mydocker.com'
    }
    // 必须包含此步骤
    stages {

        // stage('set TAG & ENV & harbor_registry'){
        //     steps {
        //         script {
        //             if(params.BRANCH=='master'){
        //                     env.TAG= sh(returnStdout: true,script: 'git describe --tags `git rev-list --tags --max-count=1`')
        //                     env.ENV='prod'
        //                     // 正式应该是阿里云
        //                     env.HARBOR_REGISTRY = 'myhub.mydocker.com'
        //             }else {
        //                     env.TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
        //                     env.ENV='dev'
        //                     env.HARBOR_REGISTRY = 'myhub.mydocker.com'
        //             }
        //         }

        //     }
        // }
        stage('display var') {
            steps {
                echo "Runing ${env.BUILD_ID}"
                echo "BRANCH ${params.BRANCH}"
                echo "tag: $TAG  replicas: ${params.REPLICAS} harbor: ${HARBOR_REGISTRY}"
            }
        }
        stage('checkout') {
            // when {
            //     expression { return params.ACTION == "deploy" }
            // }
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
                sh '''
                    cd $WORKSPACE/k8s/
                    sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
                '''
            }
        }

        stage('deploy prod'){
            when {
                allOf {
                    environment name: 'ACTION', value: 'deploy'
                }
            }
            steps {
                 //  sh -x   build.sh --action=deploy --env=prod  --project=ms --service=flask-k8s --tag=$tag --replicas=1 --type=$type --canary_weight=$canary_weight
                 echo "$TYPE $CANARY_WEIGHT"
                 sh '''
                    cd $WORKSPACE/k8s/
                    sh  build.sh --action=deploy --env=prod --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS  --type=$TYPE --canary_weight=$CANARY_WEIGHT --harbor_registry=$HARBOR_REGISTRY 
                '''
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