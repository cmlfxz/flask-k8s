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
        gitParameter (
            name: 'BRANCH', 
            branchFilter: 'origin/(.*)', 
            defaultValue: 'develop', 
            type: 'PT_BRANCH',
            description:"git branch choice"
        )
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

        // choice(
        //     description: '正式环境发布类型 ?',
        //     name: 'TYPE',
        //     choices: ['canary', 'ab']
        // )
        // choice(
        //     description: '正式环境灰度值',
        //     name: 'CANARY_WEIGHT',
        //     choices: ['10','20','30','40','50','60','70','80','90','100']
        // )
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
                    if(params.BRANCH=='master'){
                            env.TAG= sh(returnStdout: true,script: 'git describe --tags `git rev-list --tags --max-count=1`')
                            env.ENV='prod'
                            // 正式应该是阿里云
                            env.HARBOR_REGISTRY = 'myhub.mydocker.com'
                    }else {
                            env.TAG = sh(  returnStdout: true, script: 'git rev-parse --short HEAD')
                            env.ENV='dev'
                            env.HARBOR_REGISTRY = 'myhub.mydocker.com'
                    }
                }

            }
        }
        stage('display var') {
            steps {
                echo "Runing ${env.BUILD_ID}"
                echo "BRANCH ${params.BRANCH}"
                echo "tag: $TAG  replicas: ${params.REPLICAS} "

                echo "params"
                echo "${params.BRANCH}"
                echo "${params.ACTION}"
                echo "env"
                echo "${env.BRANCH}"
                echo "${env.ACTION}"
            }
        }
        stage('checkout') {
            // when {
            //     expression { return params.ACTION == "deploy" }
            // }
            steps {
                script {
                    if(params.BRANCH=='master') {
                        // revision = params.TAG 
                        revision = env.TAG 
                    }else { 
                        revision = params.BRANCH 
                    }
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
        // 分支为master时,先输入动作发布还是回滚，发布需要选择ab 还是 canary，canary还需要输入灰度值
        // stage('master get user input'){
        //     when {
        //         expression { return params.BRANCH == "master" }
        //     }
        //     input {
        //         message "Should we continue?"
        //         ok "Yes, we should."
        //         parameters {
        //             choice(
        //                 description: '发布还是回滚，生产才有回滚操作',
        //                 name: 'ACTION',
        //                 choices: ['deploy','rollout']
        //             )
        //         }
        //     }
        //     script {
        //         echo env.Action
        //         if (env.ACTION=='rollout'){
        //             //  bug build.sh检查rollout存不存在需要用到tag
        //             sh '''
        //                 cd $WORKSPACE/k8s/
        //                 sh  build.sh --action=rollout --env=prod --project=$PROJECT  --tag=$TAG
        //             '''
        //         }
        //     }
        // }

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
        // stage('build') {
        //     steps {
        //         echo  "$TAG, $ENV" 
        //         sh '''
        //             echo "$BRANCH"
        //             if [[ "$BRANCH" = "master" ]];then
        //                 ENV='prod'
        //             else
        //                 TAG=$(git rev-parse --short HEAD)
        //                 ENV='dev'
        //             fi
        //             echo $TAG,$ENV
        //             cd $WORKSPACE/k8s/
        //             sh build.sh --action=build --env=$ENV --project=$PROJECT --service=$SERVICE --tag=$TAG --harbor_registry=$HARBOR_REGISTRY
        //         '''
        //     }
        // }
        stage('deploy dev'){
            when {
                allOf {
                    // branch 'develop';
                    environment name: 'BRANCH', value: 'develop';
                    environment name: 'ACTION', value: 'deploy' 
                }
                
            }
            steps {
                 sh '''
                    cd $WORKSPACE/k8s/
                    sh  build.sh --action=deploy --env=dev --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS --harbor_registry=$HARBOR_REGISTRY 
                '''
            }
        }
        stage('deploy prod'){
            when {
                allOf {
                    // expression { return params.BRANCH == "master" };
                    // expression { return params.ACTION == "deploy" }
                    environment name: 'BRANCH', value: 'develop';
                    environment name: 'ACTION', value: 'deploy' 
                }
            }
            // steps {
            //     echo  "${env.BRANCH}"
            // }

            stages {
                stage('input deploy type') {
                    input {
                        message "Should we continue?"
                        ok "Yes, we should."
                        parameters {
                            choice(
                                description: '正式环境发布类型 ?',
                                name: 'TYPE',
                                choices: ['canary', 'ab']
                            )
                        }
                    }

                    steps {
                        echo  "$TYPE ${env.TYPE}"
                        // script {
                        //     if(params.TYPE=='ab') {
                        //         echo "1"
                        //         env.TYPE='ab'
                        //     }else{
                        //         echo  "2"
                        //         env.TYPE='canary'
                        //     }
                        // }
                    }

                }
                stage('exec canary deploy') {
                    when {
                        False
                        // expression { return params.TYPE=='ab' } 
                    }
                    stages{
                        stage('input canary type') {
                            input {
                                message "Should we continue?"
                                ok "Yes, we should."
                                parameters {
                                    choice(
                                        description: '正式环境初始灰度值',
                                        name: 'CANARY_WEIGHT',
                                        choices: ['10','20','30','40','50','60','70','80','90','100']
                                    )
                                }
                            }
                            steps {
                                echo "$TYPE $CANARY_WEIGHT"
                                echo "pp执行灰度发布"
                                sh '''
                                    cd $WORKSPACE/k8s/
                                    sh  build.sh --action=deploy --env=prod --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS  --type=canary --canary_weight=$CANARY_WEIGHT --harbor_registry=$HARBOR_REGISTRY 
                                '''
                            }
                        }
                    }

                }
                stage('exec ab deploy') {
                    when {
                        expression { return env.TYPE == "ab" }
                    }
                    steps {
                        sh '''
                            cd $WORKSPACE/k8s/
                            sh  build.sh --action=deploy --env=prod --project=$PROJECT --service=$SERVICE --tag=$TAG --replicas=$REPLICAS  --type=ab  --harbor_registry=$HARBOR_REGISTRY 
                        '''
                    }

                }
                
            }

        }
        stage('rollout'){
            
            when {
                allOf {
                    // branch 'master' ;
                    environment name: 'BRANCH', value: 'master';
                    environment name: 'ACTION', value: 'rollout' 
                }
            }
            steps {
                //  bug build.sh检查rollout存不存在需要用到tag
                 sh '''
                    cd $WORKSPACE/k8s/
                    sh  build.sh --action=rollout --env=prod --project=$PROJECT  --tag=$TAG
                '''
            }
        }
    }

}