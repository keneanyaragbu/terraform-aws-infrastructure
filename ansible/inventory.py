#!/usr/bin/env python3
"""
Dynamic Ansible Inventory Script
Reads Terraform outputs and generates Ansible inventory
Author: Anyaragbu Kenechukwu
"""

import json
import subprocess
import sys
import os

def get_terraform_outputs():
    """Get outputs from Terraform state"""
    try:
        # Change to terraform directory
        terraform_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        result = subprocess.run(
            ['terraform', 'output', '-json'],
            capture_output=True,
            text=True,
            cwd=terraform_dir
        )
        
        if result.returncode != 0:
            print(f"Error getting Terraform outputs: {result.stderr}", file=sys.stderr)
            sys.exit(1)
            
        return json.loads(result.stdout)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def get_app_server_ips(bastion_ip):
    """Get private IPs of app servers via AWS CLI"""
    try:
        result = subprocess.run([
            'aws', 'ec2', 'describe-instances',
            '--filters',
            'Name=tag:Name,Values=my-production-app-server',
            'Name=instance-state-name,Values=running',
            '--query',
            'Reservations[].Instances[].PrivateIpAddress',
            '--output', 'json',
            '--region', 'us-east-1'
        ],
        capture_output=True,
        text=True
        )
        
        if result.returncode != 0:
            print(f"Error getting app server IPs: {result.stderr}", file=sys.stderr)
            sys.exit(1)
            
        return json.loads(result.stdout)
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def generate_inventory():
    """Generate Ansible inventory from Terraform outputs"""
    
    # Get Terraform outputs
    outputs = get_terraform_outputs()
    
    # Extract values
    bastion_ip = outputs.get('bastion_public_ip', {}).get('value', '')
    key_path = os.path.expanduser('~/.ssh/key.pem')
    
    # Get app server IPs
    app_server_ips = get_app_server_ips(bastion_ip)
    
    # Generate inventory
    inventory = {
        "all": {
            "children": {
                "bastion": {},
                "app_servers": {}
            }
        },
        "bastion": {
            "hosts": {
                "bastion_host": {
                    "ansible_host": bastion_ip,
                    "ansible_user": "ec2-user",
                    "ansible_ssh_private_key_file": key_path,
                    "ansible_ssh_common_args": "-o StrictHostKeyChecking=no"
                }
            }
        },
        "app_servers": {
            "hosts": {}
        },
        "_meta": {
            "hostvars": {}
        }
    }
    
    # Add app servers
    for i, ip in enumerate(app_server_ips, 1):
        host_name = f"app_server_{i}"
        inventory["app_servers"]["hosts"][host_name] = {
            "ansible_host": ip,
            "ansible_user": "ec2-user",
            "ansible_ssh_private_key_file": key_path,
            "ansible_ssh_common_args": (
                f"-o StrictHostKeyChecking=no "
                f"-o ProxyCommand='ssh -W %h:%p -i {key_path} "
                f"-o StrictHostKeyChecking=no ec2-user@{bastion_ip}'"
            )
        }
        inventory["_meta"]["hostvars"][host_name] = {
            "ansible_host": ip
        }
    
    return inventory

if __name__ == '__main__':
    inventory = generate_inventory()
    print(json.dumps(inventory, indent=2))
