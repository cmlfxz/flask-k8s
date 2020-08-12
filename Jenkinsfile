pipeline {
    agent any
    parameters {
        gitParameter branchFilter: 'origin/(.*)', defaultValue: 'develop', name: 'BRANCH', \
                        type: 'PT_BRANCH',description:"git branch choice"
    }
    # 必须包含此步骤
    stages {
        stage('display var') {
            steps {
                echo "Runing $(env.BUILD_ID)"
                echo "BRANCH ${params.BRANCH}"
            }
        }
    }
}