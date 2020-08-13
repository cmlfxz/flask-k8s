pipeline {
    agent any
    parameters {
        // gitParameter branchFilter: 'origin/(.*)', defaultValue: 'develop', name: 'BRANCH', \
        //                 type: 'PT_BRANCH',description:"git branch choice"
        string(
            description: '副本数',
            name: 'REPLICAS',
            defaultValue: "1"
        )
        choice(
            description: '你需要选择哪个模块进行构建 ?',
            name: 'SERVICE',
            choices: ['flask-k8s', 'flask-tutorial']
        )
    }
    environment {
        ENV = 'dev'
        PROJECT = 'ms'
        // SERVICE = 'flask-k8s'
        HARBOR_REGISTRY = 'myhub.mydocker.com'
        // 用这个作为dev的tag 最新的commit id
        // TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
        BRANCH=sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD').trim()
    }
    // 必须包含此步骤
    stages {
        stage('get tag') {
            steps {
                script {
                    if(env.BRANCH=='master'){
                        sh '''
                            git fetch --tags
                        '''
                        TAG= sh( returnStdout: true, script: 'git describe --tags `git rev-list --tags --max-count=1`')
                    }else {
                        TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
                    }
                }
            }
        }
        stage('display var') {
            steps {
                echo "Runing ${env.BUILD_ID}"
                echo "BRANCH ${env.BRANCH}"
                echo "tag: $TAG  replicas: ${params.REPLICAS}"
            }
        }
        // stage('build'){
        //     steps {
        //         sh '''
        //             cd $WORKSPACE/k8s/
        //             sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
        //         '''
        //     }
        // }
        // stage('deploy'){
        //     steps {
        //          sh '''
        //             cd $WORKSPACE/k8s/
        //             sh  build.sh --action=deploy --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS --harbor_registry=$HARBOR_REGISTRY 
        //         '''
        //     }
        // }
    }

}