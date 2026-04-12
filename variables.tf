variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name used for tagging"
  type        = string
  default     = "my-production"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_az1_cidr" {
  description = "Public subnet AZ1 CIDR"
  type        = string
  default     = "10.0.1.0/24"
}

variable "public_subnet_az2_cidr" {
  description = "Public subnet AZ2 CIDR"
  type        = string
  default     = "10.0.2.0/24"
}

variable "private_subnet_az1_cidr" {
  description = "Private subnet AZ1 CIDR"
  type        = string
  default     = "10.0.3.0/24"
}

variable "private_subnet_az2_cidr" {
  description = "Private subnet AZ2 CIDR"
  type        = string
  default     = "10.0.4.0/24"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
}

variable "key_name" {
  description = "EC2 key pair name"
  type        = string
  default     = "key"
}

variable "domain_name" {
  description = "Domain name for Route 53"
  type        = string
  default     = "kaydev.online"
}

variable "ami_id" {
  description = "AMI ID for EC2 instances"
  type        = string
  default     = "ami-0ea87431b78a82070"
}