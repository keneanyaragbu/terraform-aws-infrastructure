# Terraform AWS Infrastructure
# Author: Anyaragbu Kenechukwu Nnaemeka
# Description: Production grade AWS infrastructure
# Tools: Terraform, Ansible, Python

# This file serves as the entry point for the infrastructure
# All resources are organized in separate files:
# - vpc.tf        : VPC, Subnets, IGW, NAT, Route Tables
# - security.tf   : Security Groups
# - compute.tf    : EC2, Bastion, Launch Template
# - loadbalancer.tf: ALB, Target Group, Listener
# - asg.tf        : Auto Scaling Group, CloudWatch Alarms
# - route53.tf    : Route 53 Records
# - outputs.tf    : Output Values
# - variables.tf  : Input Variables
# - providers.tf  : AWS Provider Configuration