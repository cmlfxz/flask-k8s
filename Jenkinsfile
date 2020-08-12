pipeline {
    agent any
    parameters {
        gitParameter branchFilter: 'origin/(.*)', defaultValue: 'develop', name: 'BRANCH', \
                        type: 'PT_BRANCH',description:"git branch choice"
    }
}