pipeline {
    agent any
    parameters {
        gitParameter branchFilter: 'origin/(.*)', defaultValue: 'develop', name: 'BRANCH', \
                        type: 'PT_BRANCH',description:"git branch choice"
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
        TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
    }
    // 必须包含此步骤
    stages {
        stage('display var') {
            steps {
                echo "Runing ${env.BUILD_ID}"
                echo "BRANCH ${params.BRANCH}"
                echo "tag: $TAG  replicas: ${params.REPLICAS}"
            }
        }
        stage('build'){
            // sh  build.sh build dev ms flask-k8s $commit
            steps {
                sh '''
                    cd $WORKSPACE/k8s/
                    sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
                '''
            }
        }
        stage('deploy'){
            // sh  build.sh deploy dev ms flask-k8s $commit 1
            steps {
                 sh '''
                    cd $WORKSPACE/k8s/
                    sh  build.sh --action=deploy --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS --harbor_registry=$HARBOR_REGISTRY 
                '''
            }
        }
    }

}