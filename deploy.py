#!/usr/bin/env python3
"""
Production Deployment Orchestration Script
Author: Anyaragbu Kenechukwu
Description: Orchestrates Terraform + Ansible deployment
"""

import subprocess
import json
import time
import sys
import os
from datetime import datetime

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def log(message, color=Colors.BLUE):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}{Colors.BOLD}[{timestamp}] {message}{Colors.END}")

def success(message):
    log(f"✅ {message}", Colors.GREEN)

def error(message):
    log(f"❌ {message}", Colors.RED)
    sys.exit(1)

def warning(message):
    log(f"⚠️  {message}", Colors.YELLOW)

def run_command(command, cwd=None, capture=False):
    """Run a shell command and return result"""
    log(f"Running: {' '.join(command)}")
    
    if capture:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            cwd=cwd
        )
        return result
    else:
        result = subprocess.run(
            command,
            cwd=cwd
        )
        return result

def terraform_init():
    """Initialize Terraform"""
    log("Initializing Terraform...")
    result = run_command(['terraform', 'init'])
    if result.returncode != 0:
        error("Terraform init failed!")
    success("Terraform initialized!")

def terraform_plan():
    """Run Terraform plan"""
    log("Running Terraform plan...")
    result = run_command(['terraform', 'plan', '-out=tfplan'])
    if result.returncode != 0:
        error("Terraform plan failed!")
    success("Terraform plan complete!")

def terraform_apply():
    """Apply Terraform plan"""
    log("Applying Terraform plan...")
    result = run_command(['terraform', 'apply', 'tfplan'])
    if result.returncode != 0:
        error("Terraform apply failed!")
    success("Infrastructure provisioned successfully!")

def get_terraform_outputs():
    """Get Terraform outputs"""
    log("Getting Terraform outputs...")
    result = run_command(
        ['terraform', 'output', '-json'],
        capture=True
    )
    if result.returncode != 0:
        error("Failed to get Terraform outputs!")
    
    outputs = json.loads(result.stdout)
    return outputs

def wait_for_instances(timeout=300):
    """Wait for EC2 instances to be running and healthy"""
    log("Waiting for EC2 instances to be ready...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        result = run_command([
            'aws', 'ec2', 'describe-instances',
            '--filters',
            'Name=tag:Name,Values=my-production-app-server',
            'Name=instance-state-name,Values=running',
            '--query',
            'Reservations[].Instances[].InstanceId',
            '--output', 'json',
            '--region', 'us-east-1'
        ], capture=True)
        
        if result.returncode == 0:
            instances = json.loads(result.stdout)
            if len(instances) >= 2:
                success(f"Found {len(instances)} running instances!")
                # Wait extra time for user data to complete
                log("Waiting 60 seconds for user data to complete...")
                time.sleep(60)
                return True
        
        warning(f"Waiting for instances... ({int(time.time() - start_time)}s)")
        time.sleep(15)
    
    error(f"Timeout waiting for instances after {timeout} seconds!")

def run_ansible():
    """Run Ansible playbook"""
    log("Running Ansible playbook...")
    
    ansible_dir = os.path.join(os.path.dirname(__file__), 'ansible')
    
    result = run_command([
        'ansible-playbook',
        '-i', 'inventory.py',
        'playbook.yml',
        '-v'
    ], cwd=ansible_dir)
    
    if result.returncode != 0:
        error("Ansible playbook failed!")
    success("Ansible configuration complete!")

def verify_deployment(outputs):
    """Verify the deployment is working"""
    log("Verifying deployment...")
    
    alb_dns = outputs.get('alb_dns_name', {}).get('value', '')
    
    if not alb_dns:
        warning("Could not get ALB DNS name for verification")
        return
    
    log(f"Testing ALB: http://{alb_dns}")
    
    # Wait for ALB health checks
    log("Waiting 30 seconds for ALB health checks...")
    time.sleep(30)
    
    result = run_command([
        'curl', '-s', '-o', '/dev/null',
        '-w', '%{http_code}',
        f'http://{alb_dns}'
    ], capture=True)
    
    if result.stdout == '200':
        success(f"Deployment verified! Site is live at http://{alb_dns}")
    else:
        warning(f"Site returned status: {result.stdout} — may need more time")

def print_summary(outputs):
    """Print deployment summary"""
    print("\n")
    print(f"{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}   DEPLOYMENT COMPLETE!{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"\n{Colors.BOLD}Infrastructure Details:{Colors.END}")
    print(f"  Website URL:    http://kaydev.online")
    print(f"  ALB DNS:        {outputs.get('alb_dns_name', {}).get('value', 'N/A')}")
    print(f"  Bastion IP:     {outputs.get('bastion_public_ip', {}).get('value', 'N/A')}")
    print(f"  NAT Gateway:    {outputs.get('nat_gateway_ip', {}).get('value', 'N/A')}")
    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
    print(f"  1. Update GoDaddy nameservers if changed")
    print(f"  2. Check CloudWatch alarms")
    print(f"  3. Verify Grafana dashboard")
    print(f"  4. Confirm SNS email subscription")
    print(f"\n{Colors.BOLD}To destroy infrastructure:{Colors.END}")
    print(f"  terraform destroy")
    print(f"\n{Colors.GREEN}{Colors.BOLD}{'='*60}{Colors.END}\n")

def main():
    """Main deployment orchestration"""
    
    print(f"\n{Colors.BLUE}{Colors.BOLD}")
    print("="*60)
    print("   Production AWS Infrastructure Deployment")
    print("   Author: Anyaragbu Kenechukwu")
    print("   Tools: Terraform + Ansible + Python")
    print("="*60)
    print(f"{Colors.END}\n")
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # Phase 1 — Terraform
        log("PHASE 1: Infrastructure Provisioning with Terraform")
        terraform_init()
        terraform_plan()
        terraform_apply()
        
        # Get outputs
        outputs = get_terraform_outputs()
        
        # Phase 2 — Wait for instances
        log("PHASE 2: Waiting for EC2 instances to be ready")
        wait_for_instances()
        
        # Phase 3 — Ansible
        log("PHASE 3: Server Configuration with Ansible")
        run_ansible()
        
        # Phase 4 — Verify
        log("PHASE 4: Verifying Deployment")
        verify_deployment(outputs)
        
        # Print summary
        print_summary(outputs)
        
    except KeyboardInterrupt:
        warning("Deployment interrupted by user!")
        sys.exit(1)

if __name__ == '__main__':
    main()
