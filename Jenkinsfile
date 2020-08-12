pipeline {
    agent any
    parameters {
        gitParameter branchFilter: 'origin/(.*)', defaultValue: 'develop', name: 'BRANCH', \
                        type: 'PT_BRANCH',description:"git branch choice"
        string(
            description: '副本数',
            name: 'REPLICAS',
            defaultValue: '1'
        )
    }
    environment {
        ENV = 'dev'
        PROJECT = 'ms'
        SERVICE = 'flask-k8s'
        HARBOR_REGISTRY = 'myhun.mydocker.com'
        // 用这个作为dev的tag
        TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
    }
    // 必须包含此步骤
    stages {
        stage('display var') {
            steps {
                echo "Runing ${env.BUILD_ID}"
                echo "BRANCH ${params.BRANCH}"
                echo "tag: $COMMIT_ID  replicas: $params.REPLICAS"
            }
        }
        stage('build'){
            // sh  build.sh build dev ms flask-k8s $commit

            '''
                cd $WORKSPACE/k8s/$ENV
                sh build.sh build $ENV $PROJECT $SERVICE $TAG
            '''
        }
        stage('deploy'){
            // sh  build.sh deploy dev ms flask-k8s $commit 1
            '''
                cd $WORKSPACE/k8s/$ENV
                sh  build.sh deploy $ENV $PROJECT $SERVICE $TAG $params.REPLICAS
            '''
        }
    }

}