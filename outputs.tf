# VPC
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

# Subnets
output "public_subnet_az1_id" {
  description = "Public Subnet AZ1 ID"
  value       = aws_subnet.public_az1.id
}

output "public_subnet_az2_id" {
  description = "Public Subnet AZ2 ID"
  value       = aws_subnet.public_az2.id
}

output "private_subnet_az1_id" {
  description = "Private Subnet AZ1 ID"
  value       = aws_subnet.private_az1.id
}

output "private_subnet_az2_id" {
  description = "Private Subnet AZ2 ID"
  value       = aws_subnet.private_az2.id
}

# Bastion Host
output "bastion_public_ip" {
  description = "Bastion Host Public IP"
  value       = aws_eip.bastion.public_ip
}

# Load Balancer
output "alb_dns_name" {
  description = "ALB DNS Name"
  value       = aws_lb.main.dns_name
}

# Route 53
output "nameservers" {
  description = "Update these nameservers in GoDaddy"
  value       = aws_route53_zone.main.name_servers
}

output "website_url" {
  description = "Website URL"
  value       = "http://${var.domain_name}"
}

# NAT Gateway
output "nat_gateway_ip" {
  description = "NAT Gateway Public IP"
  value       = aws_eip.nat.public_ip
}