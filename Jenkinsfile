pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        AWX_URL = 'http://3.90.20.153:30701'
        INVENTORY_ID = '11'
        JOB_TEMPLATE_ID = '3'
    }

    stages {

        stage('Install Dependencies') {
            steps {
                sh 'pip3 install requests'
            }
        }

        stage('Terraform') {
            steps {
                sh '''
                terraform init
                terraform apply -auto-approve
                '''
            }
        }

        stage('AWX Deploy') {
            steps {
                withCredentials([string(credentialsId: 'awx-token', variable: 'AWX_TOKEN')]) {
                    sh 'python3 scripts/jenkins_awx_deploy.py'
                }
            }
        }
    }
}
