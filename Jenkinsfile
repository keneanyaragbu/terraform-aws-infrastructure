pipeline {
    agent any

    parameters {
        choice(
            name: 'ACTION',
            choices: ['deploy', 'destroy'],
            description: 'Deploy builds infrastructure and configures servers. Destroy tears everything down.'
        )
    }

    environment {
        AWS_REGION = 'us-east-1'
        AWX_URL = 'http://3.90.20.153:30701'
        INVENTORY_ID = '3'
        JOB_TEMPLATE_ID = '11'
    }

    stages {

        stage('Install Dependencies') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                sh 'pip3 install requests'
            }
        }

        stage('Terraform Apply') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                sh '''
                    terraform init
                    terraform apply -auto-approve
                '''
            }
        }

        stage('AWX Deploy') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                withCredentials([string(credentialsId: 'awx-token', variable: 'AWX_TOKEN')]) {
                    sh 'python3 scripts/jenkins_awx_deploy.py'
                }
            }
        }

        stage('Verify Deployment') {
            when { expression { params.ACTION == 'deploy' } }
            steps {
                sh '''
                    echo "==> Waiting for ALB health check..."
                    sleep 30
                    ALB_DNS=$(terraform output -raw alb_dns_name)
                    curl -f http://${ALB_DNS} || echo "ALB not ready yet — check manually"
                    echo ""
                    echo "========================================="
                    echo "  DEPLOYMENT COMPLETE"
                    echo "========================================="
                    echo "  Website:  http://$(terraform output -raw website_url)"
                    echo "  ALB:      http://${ALB_DNS}"
                    echo "  Bastion:  $(terraform output -raw bastion_public_ip)"
                    echo "========================================="
                '''
            }
        }

        stage('Terraform Destroy') {
            when { expression { params.ACTION == 'destroy' } }
            steps {
                sh '''
                    terraform init
                    terraform destroy -auto-approve
                '''
            }
        }
    }
}