# Production Infrastructure Automation Platform

**Author:** Kenechukwu Anyaragbu

Fully automated infrastructure provisioning and configuration management platform
for a Node.js application on AWS. A single Jenkins pipeline provisions cloud
infrastructure with Terraform, discovers dynamic resources, configures servers
through Ansible (AWX), and delivers a production-ready application behind a
load balancer — with zero manual intervention.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  AUTOMATION LAYER                                                   │
│                                                                     │
│  Jenkins ──► Terraform Apply ──► Python Script ──► AWX/Ansible      │
│  (CI/CD)     (Provision)         (Bridge)          (Configure)      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AWS INFRASTRUCTURE                                                 │
│                                                                     │
│  ┌── VPC (10.0.0.0/16) ──────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  Public Subnets (AZ1 + AZ2)     Private Subnets (AZ1 + AZ2)  │  │
│  │  ┌─────────────────────┐        ┌──────────────────────────┐  │  │
│  │  │ • Bastion Host      │        │ • App Server 1 (ASG)     │  │  │
│  │  │ • ALB               │──SSH──►│ • App Server 2 (ASG)     │  │  │
│  │  │ • NAT Gateway       │        │   (Nginx → Node.js:3000) │  │  │
│  │  └─────────────────────┘        └──────────────────────────┘  │  │
│  │         │                                │                     │  │
│  │    Internet GW                      NAT Gateway               │  │
│  │    (inbound traffic)             (outbound packages)          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Route 53 ──► ALB ──► Target Group ──► App Servers                  │
│  (DNS)        (Load Balance)           (Private Subnet)             │
│                                                                     │
│  SNS ──► CloudWatch Alarms ──► Email Alerts                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Traffic Flow

```
User → kaydev.online → Route 53 → ALB (public) → App Server (private)
                                                    → Nginx (port 80)
                                                    → Node.js (port 3000)
```

### Management Flow

```
Jenkins Pipeline
  │
  ├── Terraform Apply
  │     └── Creates: VPC, subnets, IGW, NAT, bastion, ALB, ASG, Route53, SNS
  │
  ├── Python Script (jenkins_awx_deploy.py)
  │     ├── Reads bastion IP from Terraform output
  │     ├── Discovers worker IPs from AWS API (by EC2 tag)
  │     ├── Clears old AWX inventory
  │     ├── Adds fresh worker IPs to app_servers group
  │     ├── Configures bastion as SSH jump host
  │     └── Launches AWX Job Template via REST API
  │
  └── AWX runs Ansible playbook
        ├── SSH path: AWX → Bastion (ec2-user) → Worker (ec2-user)
        ├── Role: security (OS hardening, firewall)
        ├── Role: nodejs (Node.js, PM2, app deployment)
        ├── Role: nginx (reverse proxy)
        ├── Role: monitoring (Prometheus Node Exporter)
        └── Post-task: health check http://localhost:3000
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| CI/CD | Jenkins | Pipeline orchestration |
| Infrastructure | Terraform | AWS resource provisioning |
| Configuration | Ansible (AWX) | Server configuration and app deployment |
| Compute | AWS EC2 (ASG) | Auto-scaled application servers |
| Networking | AWS VPC, ALB, NAT, Route 53 | Network isolation, load balancing, DNS |
| Security | Security Groups, Bastion Host | Network access control, SSH jump host |
| Monitoring | Prometheus Node Exporter, SNS | Metrics collection, alerting |
| Application | Node.js, PM2, Nginx | Runtime, process manager, reverse proxy |

---

## Repository Structure

```
├── main.tf                          # VPC, subnets, internet gateway, NAT gateway
├── compute.tf                       # Bastion host EC2, launch template
├── asg.tf                           # Auto Scaling Group for app servers
├── security.tf                      # Security groups: bastion, ALB, app servers
├── loadbalancer.tf                  # ALB, target group, listeners, health checks
├── route53.tf                       # Hosted zone, DNS records
├── sns.tf                           # SNS topic for CloudWatch alerts
├── variables.tf                     # Input variables
├── outputs.tf                       # Terraform outputs (IPs, DNS, URLs)
├── providers.tf                     # AWS provider configuration
├── Jenkinsfile                      # CI/CD pipeline definition
│
├── ansible/
│   ├── playbook.yml                 # Main playbook — runs all 4 roles
│   ├── inventory.py                 # Dynamic inventory script
│   ├── group_vars/
│   │   └── all.yml                  # Global variables (ports, domain, app config)
│   └── roles/
│       ├── security/
│       │   ├── tasks/main.yml       # Firewall, SSH hardening, app user creation
│       │   └── handlers/main.yml    # Service restart handlers
│       ├── nodejs/
│       │   ├── tasks/main.yml       # Node.js install, PM2 setup, app deployment
│       │   └── files/server.js      # Application source code
│       ├── nginx/
│       │   ├── tasks/main.yml       # Nginx install and configuration
│       │   ├── handlers/main.yml    # Nginx restart handler
│       │   └── templates/
│       │       └── nginx.conf.j2    # Nginx config template (reverse proxy)
│       └── monitoring/
│           └── tasks/main.yml       # Prometheus Node Exporter install
│
└── scripts/
    └── jenkins_awx_deploy.py        # Terraform→AWX bridge script
```

---

## Infrastructure Components

### Networking

| Resource | Purpose |
|----------|---------|
| VPC (10.0.0.0/16) | Isolated network for the entire platform |
| Public Subnet AZ1 + AZ2 | Bastion host, ALB, NAT gateway |
| Private Subnet AZ1 + AZ2 | Application servers (no public IPs) |
| Internet Gateway | Inbound traffic to ALB and bastion |
| NAT Gateway | Outbound internet for private subnet (package installs) |
| Route Tables | Public → IGW, Private → NAT |

### Security

| Resource | Inbound Rules |
|----------|--------------|
| Bastion SG | SSH (22) from Jenkins IP + AWX IP |
| ALB SG | HTTP (80) and HTTPS (443) from anywhere |
| App Server SG | SSH (22) from bastion SG only, port 3000 from ALB SG only |

The bastion host is the only SSH entry point into the private subnet.
App servers have no public IPs and accept SSH only from the bastion.
This is the standard bastion/jump-host security pattern.

### Compute

| Resource | Detail |
|----------|--------|
| Bastion Host | t2.micro, public subnet, Elastic IP |
| App Servers | ASG with launch template, private subnet |
| AMI | Amazon Linux 2023 |
| Key Pair | `key` — shared across bastion and workers |

### Load Balancing

| Resource | Detail |
|----------|--------|
| ALB | Application Load Balancer across 2 AZs |
| Target Group | Health check on port 80, routes to app servers |
| Listener | Port 80 → target group |

### DNS and Alerting

| Resource | Detail |
|----------|--------|
| Route 53 | Hosted zone for kaydev.online, A record → ALB |
| SNS | Alert topic for CloudWatch alarms → email notification |

---

## Ansible Roles

### Role: security

Hardens the operating system before any application is installed.

| Task | What it does |
|------|-------------|
| Create application user | Creates `appuser` for running the app (not root) |
| Install firewalld | Installs and enables the firewall |
| Allow SSH (22) | Opens SSH for management access |
| Allow HTTP (80) | Opens HTTP for Nginx |
| Allow app port (3000) | Opens the Node.js application port |
| Allow Node Exporter (9100) | Opens the monitoring metrics port |
| Disable root SSH | Prevents root login via SSH |
| Set SSH idle timeout | Auto-disconnects idle SSH sessions |

### Role: nodejs

Installs Node.js, deploys the application, and configures PM2 process manager.

| Task | What it does |
|------|-------------|
| Install prerequisites | ca-certificates for HTTPS |
| Add NodeSource repo | Adds the official Node.js RPM repository |
| Install Node.js | Installs Node.js 18 from NodeSource |
| Create app directory | /home/appuser/app owned by appuser |
| Copy application | Deploys server.js to the app directory |
| Install PM2 | Global install of PM2 process manager |
| Start app with PM2 | Runs server.js on port 3000 |
| Configure PM2 startup | Ensures the app survives server reboots |

### Role: nginx

Installs Nginx as a reverse proxy in front of the Node.js application.

| Task | What it does |
|------|-------------|
| Install Nginx | Installs Nginx via dnf |
| Deploy config | Templates nginx.conf.j2 with domain and port variables |
| Start and enable | Ensures Nginx is running and starts on boot |

The Nginx template proxies all traffic from port 80 to localhost:3000,
adding proper headers for WebSocket support and client IP forwarding.

### Role: monitoring

Installs Prometheus Node Exporter for infrastructure metrics.

| Task | What it does |
|------|-------------|
| Create service user | node_exporter user with no shell (security) |
| Download binary | Node Exporter v1.7.0 from GitHub releases |
| Install binary | /usr/local/bin/node_exporter |
| Create systemd service | Managed as a system service |
| Start and enable | Running on port 9100, metrics at /metrics |

---

## Jenkins Pipeline

The pipeline supports two modes via a parameter: **deploy** or **destroy**.

### Deploy Mode

```
Install Dependencies → Terraform Apply → AWX Deploy → Verify Deployment
```

| Stage | What it does |
|-------|-------------|
| Install Dependencies | `pip3 install requests` for the AWX API script |
| Terraform Apply | Provisions all AWS infrastructure |
| AWX Deploy | Runs the Python bridge script → triggers Ansible |
| Verify Deployment | Curls the ALB, prints URLs |

### Destroy Mode

```
Terraform Destroy
```

Tears down all AWS resources. One click cleanup.

### Usage

Jenkins → **Build with Parameters** → select `deploy` or `destroy` → **Build**.

---

## AWX Configuration

| Component | Detail |
|-----------|--------|
| Project | Git repo with ansible/ directory |
| Inventory (ID: 3) | `terraform-targets` — dynamically populated by Python script |
| Credential | `Worker_SSH_Key` — Machine type, contains key.pem |
| Job Template (ID: 11) | Combines project + inventory + credential + playbook.yml |

### Dynamic Inventory Flow

The Python script (`scripts/jenkins_awx_deploy.py`) is the bridge between
Terraform and AWX. Static inventory doesn't work here because the ASG
creates instances with new IPs on every deployment.

```
Terraform output → bastion public IP
AWS API query    → worker private IPs (filtered by EC2 tag)
AWX API          → clear old hosts → add new hosts → set SSH jump config → launch job
```

The inventory variables set by the script:

```yaml
ansible_user: ec2-user
ansible_host_key_checking: false
ansible_ssh_common_args: '-o ForwardAgent=yes -o UserKnownHostsFile=/dev/null
  -o StrictHostKeyChecking=no -o ProxyCommand="ssh -o ForwardAgent=yes
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
  -W %h:%p ec2-user@<BASTION_IP>"'
```

This configures the SSH tunnel: AWX → bastion (jump host) → worker (private IP).
`ForwardAgent=yes` passes AWX's loaded SSH key through the tunnel.

---

## Runbooks

### Deploy New Version

```
When:    New application code ready for production
Who:     DevOps engineer
Steps:
  1. Commit code changes to main branch
  2. Jenkins → Build with Parameters → deploy → Build
  3. Monitor Jenkins console: Terraform Apply → AWX Deploy → Verify
  4. Check AWX job output: all tasks green, health check 200
  5. Verify: curl http://<ALB_DNS>
  6. Verify: open http://kaydev.online in browser
```

### Destroy Infrastructure

```
When:    End of demo, cost saving, environment teardown
Who:     DevOps engineer
Steps:
  1. Jenkins → Build with Parameters → destroy → Build
  2. Monitor Jenkins console: Terraform Destroy
  3. Verify in AWS Console: no EC2 instances, no ALB, no NAT gateway
  4. Note: Route 53 hosted zone is destroyed — nameservers will change on rebuild
```

### Rebuild After Destroy

```
When:    Need to bring the environment back up
Who:     DevOps engineer
Steps:
  1. Jenkins → Build with Parameters → deploy → Build
  2. Wait for pipeline to complete (~5-8 minutes)
  3. If domain needed: terraform output nameservers → update in GoDaddy
  4. Verify: curl http://<ALB_DNS>
  5. All infrastructure and configuration is fully automated — no manual steps
```

### SSH into App Servers (Debugging)

```
When:    Need to inspect a running app server
Who:     DevOps engineer
Steps:
  1. Add your laptop IP to bastion security group in AWS Console
  2. Get bastion IP: terraform output bastion_public_ip
  3. SSH to bastion: ssh -i key.pem ec2-user@<BASTION_IP>
  4. From bastion, SSH to worker: ssh ec2-user@<WORKER_PRIVATE_IP>
  5. Check app: pm2 status, curl localhost:3000
  6. Check nginx: systemctl status nginx, curl localhost:80
  7. Check logs: pm2 logs, journalctl -u nginx
```

### Re-run Ansible Only (No Terraform)

```
When:    Configuration change needed, infrastructure already exists
Who:     DevOps engineer
Steps:
  1. AWX UI → Templates → Job Template 11 → Launch
  2. Or: update playbook/roles in Git → AWX syncs project → launch job
  3. Monitor job output in AWX
  4. Verify: health check passes in post_tasks
```

### Rollback Application

```
When:    New deployment broke the application
Who:     DevOps engineer
Steps:
  1. Revert the commit in Git (git revert HEAD)
  2. Push to main
  3. Jenkins → Build with Parameters → deploy
  4. Pipeline re-provisions with the previous code version
  5. Verify: curl http://<ALB_DNS>
  Alternative:
  1. SSH to app server via bastion
  2. pm2 list → identify the running process
  3. Replace server.js with the previous version
  4. pm2 restart my-production
```

### Scaling

```
When:    High traffic, slow response times
Who:     DevOps engineer
Steps:
  1. AWS Console → EC2 → Auto Scaling Groups → select ASG
  2. Edit: increase desired capacity (or adjust scaling policy)
  3. New instances launch automatically in private subnet
  4. ALB health check registers them into the target group
  5. Run AWX job to configure new instances with Ansible
  6. Verify: all instances serving traffic via ALB
```

---

## Pain Points and Lessons Learned

### Bastion username mismatch
The Python script initially used `ubuntu@bastion_ip` but the AMI was
Amazon Linux 2023, which uses `ec2-user`. SSH connections timed out with
cryptic "port 65535" errors. Fix: changed the ProxyCommand to use
`ec2-user`.

### Worker username mismatch
Same issue — `ansible_user: ubuntu` in the inventory variables, but workers
also ran Amazon Linux. Changed to `ansible_user: ec2-user`.

### AWX SSH key not loaded
The AWX Machine credential had an empty SSH Private Key field. AWX attempted
SSH with no key, causing "Permission denied" on every connection. Fix:
uploaded the key.pem contents into the credential.

### ProxyCommand key forwarding
AWX loads the SSH key into an agent, but `ProxyCommand` spawns a separate
SSH process that can't access the agent. Fix: added `-o ForwardAgent=yes`
to both the outer and inner SSH commands.

### Package manager mismatch
Node.js role used `apt` (Ubuntu/Debian) but the servers ran Amazon Linux
(`yum`/`dnf`). Fix: rewrote the role to use `yum` and the NodeSource RPM
repository.

### curl-minimal conflict
Amazon Linux 2023 ships with `curl-minimal`, which conflicts with the full
`curl` package. Fix: removed `curl` from the prerequisite package list
since `curl-minimal` provides the same functionality.

### Bastion security group overwrites
`data.http.my_ip` fetches the IP of whatever machine runs `terraform apply`
(Jenkins), not the developer's laptop. Manually added IPs get overwritten
on the next apply. Fix: added a dedicated ingress rule for the AWX server
IP, and a variable for the developer's laptop IP.

### Route53 nameservers change on rebuild
Every `terraform destroy` + `terraform apply` creates a new hosted zone
with new nameservers, breaking GoDaddy's DNS delegation. In production,
the hosted zone should live outside the ephemeral Terraform state or be
protected with `lifecycle { prevent_destroy = true }`.

---

## Variables Reference

### Terraform Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| project_name | my-production | Resource naming prefix |
| key_name | key | EC2 key pair name |
| domain_name | kaydev.online | Route 53 domain |

### Ansible Variables (group_vars/all.yml)

| Variable | Value | Used by |
|----------|-------|---------|
| app_user | appuser | Security creates user, Node.js runs app as this user |
| app_dir | /home/appuser/app | Node.js deploys code here |
| app_port | 3000 | Node.js listens, Nginx proxies to, health check verifies |
| node_version | 18 | NodeSource repository version |
| nginx_port | 80 | Nginx listens, ALB health check targets |
| project_name | my-production | PM2 process name |
| domain_name | kaydev.online | Nginx server_name directive |

---

## Outputs

| Output | Description |
|--------|------------|
| vpc_id | VPC identifier |
| public_subnet_az1_id | Public subnet in AZ1 |
| public_subnet_az2_id | Public subnet in AZ2 |
| private_subnet_az1_id | Private subnet in AZ1 |
| private_subnet_az2_id | Private subnet in AZ2 |
| bastion_public_ip | Bastion host Elastic IP (SSH entry point) |
| alb_dns_name | ALB DNS (application access) |
| website_url | http://kaydev.online |
| nat_gateway_ip | NAT gateway public IP |
| nameservers | Route 53 nameservers (update in domain registrar) |
| sns_topic_arn | SNS topic for CloudWatch alerts |# Production Infrastructure Automation Platform

**Author:** Kenechukwu Anyaragbu

Fully automated infrastructure provisioning and configuration management platform
for a Node.js application on AWS. A single Jenkins pipeline provisions cloud
infrastructure with Terraform, discovers dynamic resources, configures servers
through Ansible (AWX), and delivers a production-ready application behind a
load balancer — with zero manual intervention.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  AUTOMATION LAYER                                                   │
│                                                                     │
│  Jenkins ──► Terraform Apply ──► Python Script ──► AWX/Ansible      │
│  (CI/CD)     (Provision)         (Bridge)          (Configure)      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AWS INFRASTRUCTURE                                                 │
│                                                                     │
│  ┌── VPC (10.0.0.0/16) ──────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  Public Subnets (AZ1 + AZ2)     Private Subnets (AZ1 + AZ2)  │  │
│  │  ┌─────────────────────┐        ┌──────────────────────────┐  │  │
│  │  │ • Bastion Host      │        │ • App Server 1 (ASG)     │  │  │
│  │  │ • ALB               │──SSH──►│ • App Server 2 (ASG)     │  │  │
│  │  │ • NAT Gateway       │        │   (Nginx → Node.js:3000) │  │  │
│  │  └─────────────────────┘        └──────────────────────────┘  │  │
│  │         │                                │                     │  │
│  │    Internet GW                      NAT Gateway               │  │
│  │    (inbound traffic)             (outbound packages)          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Route 53 ──► ALB ──► Target Group ──► App Servers                  │
│  (DNS)        (Load Balance)           (Private Subnet)             │
│                                                                     │
│  SNS ──► CloudWatch Alarms ──► Email Alerts                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Traffic Flow

```
User → kaydev.online → Route 53 → ALB (public) → App Server (private)
                                                    → Nginx (port 80)
                                                    → Node.js (port 3000)
```

### Management Flow

```
Jenkins Pipeline
  │
  ├── Terraform Apply
  │     └── Creates: VPC, subnets, IGW, NAT, bastion, ALB, ASG, Route53, SNS
  │
  ├── Python Script (jenkins_awx_deploy.py)
  │     ├── Reads bastion IP from Terraform output
  │     ├── Discovers worker IPs from AWS API (by EC2 tag)
  │     ├── Clears old AWX inventory
  │     ├── Adds fresh worker IPs to app_servers group
  │     ├── Configures bastion as SSH jump host
  │     └── Launches AWX Job Template via REST API
  │
  └── AWX runs Ansible playbook
        ├── SSH path: AWX → Bastion (ec2-user) → Worker (ec2-user)
        ├── Role: security (OS hardening, firewall)
        ├── Role: nodejs (Node.js, PM2, app deployment)
        ├── Role: nginx (reverse proxy)
        ├── Role: monitoring (Prometheus Node Exporter)
        └── Post-task: health check http://localhost:3000
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| CI/CD | Jenkins | Pipeline orchestration |
| Infrastructure | Terraform | AWS resource provisioning |
| Configuration | Ansible (AWX) | Server configuration and app deployment |
| Compute | AWS EC2 (ASG) | Auto-scaled application servers |
| Networking | AWS VPC, ALB, NAT, Route 53 | Network isolation, load balancing, DNS |
| Security | Security Groups, Bastion Host | Network access control, SSH jump host |
| Monitoring | Prometheus Node Exporter, SNS | Metrics collection, alerting |
| Application | Node.js, PM2, Nginx | Runtime, process manager, reverse proxy |

---

## Repository Structure

```
├── main.tf                          # VPC, subnets, internet gateway, NAT gateway
├── compute.tf                       # Bastion host EC2, launch template
├── asg.tf                           # Auto Scaling Group for app servers
├── security.tf                      # Security groups: bastion, ALB, app servers
├── loadbalancer.tf                  # ALB, target group, listeners, health checks
├── route53.tf                       # Hosted zone, DNS records
├── sns.tf                           # SNS topic for CloudWatch alerts
├── variables.tf                     # Input variables
├── outputs.tf                       # Terraform outputs (IPs, DNS, URLs)
├── providers.tf                     # AWS provider configuration
├── Jenkinsfile                      # CI/CD pipeline definition
│
├── ansible/
│   ├── playbook.yml                 # Main playbook — runs all 4 roles
│   ├── inventory.py                 # Dynamic inventory script
│   ├── group_vars/
│   │   └── all.yml                  # Global variables (ports, domain, app config)
│   └── roles/
│       ├── security/
│       │   ├── tasks/main.yml       # Firewall, SSH hardening, app user creation
│       │   └── handlers/main.yml    # Service restart handlers
│       ├── nodejs/
│       │   ├── tasks/main.yml       # Node.js install, PM2 setup, app deployment
│       │   └── files/server.js      # Application source code
│       ├── nginx/
│       │   ├── tasks/main.yml       # Nginx install and configuration
│       │   ├── handlers/main.yml    # Nginx restart handler
│       │   └── templates/
│       │       └── nginx.conf.j2    # Nginx config template (reverse proxy)
│       └── monitoring/
│           └── tasks/main.yml       # Prometheus Node Exporter install
│
└── scripts/
    └── jenkins_awx_deploy.py        # Terraform→AWX bridge script
```

---

## Infrastructure Components

### Networking

| Resource | Purpose |
|----------|---------|
| VPC (10.0.0.0/16) | Isolated network for the entire platform |
| Public Subnet AZ1 + AZ2 | Bastion host, ALB, NAT gateway |
| Private Subnet AZ1 + AZ2 | Application servers (no public IPs) |
| Internet Gateway | Inbound traffic to ALB and bastion |
| NAT Gateway | Outbound internet for private subnet (package installs) |
| Route Tables | Public → IGW, Private → NAT |

### Security

| Resource | Inbound Rules |
|----------|--------------|
| Bastion SG | SSH (22) from Jenkins IP + AWX IP |
| ALB SG | HTTP (80) and HTTPS (443) from anywhere |
| App Server SG | SSH (22) from bastion SG only, port 3000 from ALB SG only |

The bastion host is the only SSH entry point into the private subnet.
App servers have no public IPs and accept SSH only from the bastion.
This is the standard bastion/jump-host security pattern.

### Compute

| Resource | Detail |
|----------|--------|
| Bastion Host | t2.micro, public subnet, Elastic IP |
| App Servers | ASG with launch template, private subnet |
| AMI | Amazon Linux 2023 |
| Key Pair | `key` — shared across bastion and workers |

### Load Balancing

| Resource | Detail |
|----------|--------|
| ALB | Application Load Balancer across 2 AZs |
| Target Group | Health check on port 80, routes to app servers |
| Listener | Port 80 → target group |

### DNS and Alerting

| Resource | Detail |
|----------|--------|
| Route 53 | Hosted zone for kaydev.online, A record → ALB |
| SNS | Alert topic for CloudWatch alarms → email notification |

---

## Ansible Roles

### Role: security

Hardens the operating system before any application is installed.

| Task | What it does |
|------|-------------|
| Create application user | Creates `appuser` for running the app (not root) |
| Install firewalld | Installs and enables the firewall |
| Allow SSH (22) | Opens SSH for management access |
| Allow HTTP (80) | Opens HTTP for Nginx |
| Allow app port (3000) | Opens the Node.js application port |
| Allow Node Exporter (9100) | Opens the monitoring metrics port |
| Disable root SSH | Prevents root login via SSH |
| Set SSH idle timeout | Auto-disconnects idle SSH sessions |

### Role: nodejs

Installs Node.js, deploys the application, and configures PM2 process manager.

| Task | What it does |
|------|-------------|
| Install prerequisites | ca-certificates for HTTPS |
| Add NodeSource repo | Adds the official Node.js RPM repository |
| Install Node.js | Installs Node.js 18 from NodeSource |
| Create app directory | /home/appuser/app owned by appuser |
| Copy application | Deploys server.js to the app directory |
| Install PM2 | Global install of PM2 process manager |
| Start app with PM2 | Runs server.js on port 3000 |
| Configure PM2 startup | Ensures the app survives server reboots |

### Role: nginx

Installs Nginx as a reverse proxy in front of the Node.js application.

| Task | What it does |
|------|-------------|
| Install Nginx | Installs Nginx via dnf |
| Deploy config | Templates nginx.conf.j2 with domain and port variables |
| Start and enable | Ensures Nginx is running and starts on boot |

The Nginx template proxies all traffic from port 80 to localhost:3000,
adding proper headers for WebSocket support and client IP forwarding.

### Role: monitoring

Installs Prometheus Node Exporter for infrastructure metrics.

| Task | What it does |
|------|-------------|
| Create service user | node_exporter user with no shell (security) |
| Download binary | Node Exporter v1.7.0 from GitHub releases |
| Install binary | /usr/local/bin/node_exporter |
| Create systemd service | Managed as a system service |
| Start and enable | Running on port 9100, metrics at /metrics |

---

## Jenkins Pipeline

The pipeline supports two modes via a parameter: **deploy** or **destroy**.

### Deploy Mode

```
Install Dependencies → Terraform Apply → AWX Deploy → Verify Deployment
```

| Stage | What it does |
|-------|-------------|
| Install Dependencies | `pip3 install requests` for the AWX API script |
| Terraform Apply | Provisions all AWS infrastructure |
| AWX Deploy | Runs the Python bridge script → triggers Ansible |
| Verify Deployment | Curls the ALB, prints URLs |

### Destroy Mode

```
Terraform Destroy
```

Tears down all AWS resources. One click cleanup.

### Usage

Jenkins → **Build with Parameters** → select `deploy` or `destroy` → **Build**.

---

## AWX Configuration

| Component | Detail |
|-----------|--------|
| Project | Git repo with ansible/ directory |
| Inventory (ID: 3) | `terraform-targets` — dynamically populated by Python script |
| Credential | `Worker_SSH_Key` — Machine type, contains key.pem |
| Job Template (ID: 11) | Combines project + inventory + credential + playbook.yml |

### Dynamic Inventory Flow

The Python script (`scripts/jenkins_awx_deploy.py`) is the bridge between
Terraform and AWX. Static inventory doesn't work here because the ASG
creates instances with new IPs on every deployment.

```
Terraform output → bastion public IP
AWS API query    → worker private IPs (filtered by EC2 tag)
AWX API          → clear old hosts → add new hosts → set SSH jump config → launch job
```

The inventory variables set by the script:

```yaml
ansible_user: ec2-user
ansible_host_key_checking: false
ansible_ssh_common_args: '-o ForwardAgent=yes -o UserKnownHostsFile=/dev/null
  -o StrictHostKeyChecking=no -o ProxyCommand="ssh -o ForwardAgent=yes
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
  -W %h:%p ec2-user@<BASTION_IP>"'
```

This configures the SSH tunnel: AWX → bastion (jump host) → worker (private IP).
`ForwardAgent=yes` passes AWX's loaded SSH key through the tunnel.

---

## Runbooks

### Deploy New Version

```
When:    New application code ready for production
Who:     DevOps engineer
Steps:
  1. Commit code changes to main branch
  2. Jenkins → Build with Parameters → deploy → Build
  3. Monitor Jenkins console: Terraform Apply → AWX Deploy → Verify
  4. Check AWX job output: all tasks green, health check 200
  5. Verify: curl http://<ALB_DNS>
  6. Verify: open http://kaydev.online in browser
```

### Destroy Infrastructure

```
When:    End of demo, cost saving, environment teardown
Who:     DevOps engineer
Steps:
  1. Jenkins → Build with Parameters → destroy → Build
  2. Monitor Jenkins console: Terraform Destroy
  3. Verify in AWS Console: no EC2 instances, no ALB, no NAT gateway
  4. Note: Route 53 hosted zone is destroyed — nameservers will change on rebuild
```

### Rebuild After Destroy

```
When:    Need to bring the environment back up
Who:     DevOps engineer
Steps:
  1. Jenkins → Build with Parameters → deploy → Build
  2. Wait for pipeline to complete (~5-8 minutes)
  3. If domain needed: terraform output nameservers → update in GoDaddy
  4. Verify: curl http://<ALB_DNS>
  5. All infrastructure and configuration is fully automated — no manual steps
```

### SSH into App Servers (Debugging)

```
When:    Need to inspect a running app server
Who:     DevOps engineer
Steps:
  1. Add your laptop IP to bastion security group in AWS Console
  2. Get bastion IP: terraform output bastion_public_ip
  3. SSH to bastion: ssh -i key.pem ec2-user@<BASTION_IP>
  4. From bastion, SSH to worker: ssh ec2-user@<WORKER_PRIVATE_IP>
  5. Check app: pm2 status, curl localhost:3000
  6. Check nginx: systemctl status nginx, curl localhost:80
  7. Check logs: pm2 logs, journalctl -u nginx
```

### Re-run Ansible Only (No Terraform)

```
When:    Configuration change needed, infrastructure already exists
Who:     DevOps engineer
Steps:
  1. AWX UI → Templates → Job Template 11 → Launch
  2. Or: update playbook/roles in Git → AWX syncs project → launch job
  3. Monitor job output in AWX
  4. Verify: health check passes in post_tasks
```

### Rollback Application

```
When:    New deployment broke the application
Who:     DevOps engineer
Steps:
  1. Revert the commit in Git (git revert HEAD)
  2. Push to main
  3. Jenkins → Build with Parameters → deploy
  4. Pipeline re-provisions with the previous code version
  5. Verify: curl http://<ALB_DNS>
  Alternative:
  1. SSH to app server via bastion
  2. pm2 list → identify the running process
  3. Replace server.js with the previous version
  4. pm2 restart my-production
```

### Scaling

```
When:    High traffic, slow response times
Who:     DevOps engineer
Steps:
  1. AWS Console → EC2 → Auto Scaling Groups → select ASG
  2. Edit: increase desired capacity (or adjust scaling policy)
  3. New instances launch automatically in private subnet
  4. ALB health check registers them into the target group
  5. Run AWX job to configure new instances with Ansible
  6. Verify: all instances serving traffic via ALB
```

---

## Pain Points and Lessons Learned

### Bastion username mismatch
The Python script initially used `ubuntu@bastion_ip` but the AMI was
Amazon Linux 2023, which uses `ec2-user`. SSH connections timed out with
cryptic "port 65535" errors. Fix: changed the ProxyCommand to use
`ec2-user`.

### Worker username mismatch
Same issue — `ansible_user: ubuntu` in the inventory variables, but workers
also ran Amazon Linux. Changed to `ansible_user: ec2-user`.

### AWX SSH key not loaded
The AWX Machine credential had an empty SSH Private Key field. AWX attempted
SSH with no key, causing "Permission denied" on every connection. Fix:
uploaded the key.pem contents into the credential.

### ProxyCommand key forwarding
AWX loads the SSH key into an agent, but `ProxyCommand` spawns a separate
SSH process that can't access the agent. Fix: added `-o ForwardAgent=yes`
to both the outer and inner SSH commands.

### Package manager mismatch
Node.js role used `apt` (Ubuntu/Debian) but the servers ran Amazon Linux
(`yum`/`dnf`). Fix: rewrote the role to use `yum` and the NodeSource RPM
repository.

### curl-minimal conflict
Amazon Linux 2023 ships with `curl-minimal`, which conflicts with the full
`curl` package. Fix: removed `curl` from the prerequisite package list
since `curl-minimal` provides the same functionality.

### Bastion security group overwrites
`data.http.my_ip` fetches the IP of whatever machine runs `terraform apply`
(Jenkins), not the developer's laptop. Manually added IPs get overwritten
on the next apply. Fix: added a dedicated ingress rule for the AWX server
IP, and a variable for the developer's laptop IP.

### Route53 nameservers change on rebuild
Every `terraform destroy` + `terraform apply` creates a new hosted zone
with new nameservers, breaking GoDaddy's DNS delegation. In production,
the hosted zone should live outside the ephemeral Terraform state or be
protected with `lifecycle { prevent_destroy = true }`.

---

## Variables Reference

### Terraform Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| project_name | my-production | Resource naming prefix |
| key_name | key | EC2 key pair name |
| domain_name | kaydev.online | Route 53 domain |

### Ansible Variables (group_vars/all.yml)

| Variable | Value | Used by |
|----------|-------|---------|
| app_user | appuser | Security creates user, Node.js runs app as this user |
| app_dir | /home/appuser/app | Node.js deploys code here |
| app_port | 3000 | Node.js listens, Nginx proxies to, health check verifies |
| node_version | 18 | NodeSource repository version |
| nginx_port | 80 | Nginx listens, ALB health check targets |
| project_name | my-production | PM2 process name |
| domain_name | kaydev.online | Nginx server_name directive |

---

## Outputs

| Output | Description |
|--------|------------|
| vpc_id | VPC identifier |
| public_subnet_az1_id | Public subnet in AZ1 |
| public_subnet_az2_id | Public subnet in AZ2 |
| private_subnet_az1_id | Private subnet in AZ1 |
| private_subnet_az2_id | Private subnet in AZ2 |
| bastion_public_ip | Bastion host Elastic IP (SSH entry point) |
| alb_dns_name | ALB DNS (application access) |
| website_url | http://kaydev.online |
| nat_gateway_ip | NAT gateway public IP |
| nameservers | Route 53 nameservers (update in domain registrar) |
| sns_topic_arn | SNS topic for CloudWatch alerts |# Production Infrastructure Automation Platform

**Author:** Kenechukwu Anyaragbu

Fully automated infrastructure provisioning and configuration management platform
for a Node.js application on AWS. A single Jenkins pipeline provisions cloud
infrastructure with Terraform, discovers dynamic resources, configures servers
through Ansible (AWX), and delivers a production-ready application behind a
load balancer — with zero manual intervention.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  AUTOMATION LAYER                                                   │
│                                                                     │
│  Jenkins ──► Terraform Apply ──► Python Script ──► AWX/Ansible      │
│  (CI/CD)     (Provision)         (Bridge)          (Configure)      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AWS INFRASTRUCTURE                                                 │
│                                                                     │
│  ┌── VPC (10.0.0.0/16) ──────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  Public Subnets (AZ1 + AZ2)     Private Subnets (AZ1 + AZ2)  │  │
│  │  ┌─────────────────────┐        ┌──────────────────────────┐  │  │
│  │  │ • Bastion Host      │        │ • App Server 1 (ASG)     │  │  │
│  │  │ • ALB               │──SSH──►│ • App Server 2 (ASG)     │  │  │
│  │  │ • NAT Gateway       │        │   (Nginx → Node.js:3000) │  │  │
│  │  └─────────────────────┘        └──────────────────────────┘  │  │
│  │         │                                │                     │  │
│  │    Internet GW                      NAT Gateway               │  │
│  │    (inbound traffic)             (outbound packages)          │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  Route 53 ──► ALB ──► Target Group ──► App Servers                  │
│  (DNS)        (Load Balance)           (Private Subnet)             │
│                                                                     │
│  SNS ──► CloudWatch Alarms ──► Email Alerts                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Traffic Flow

```
User → kaydev.online → Route 53 → ALB (public) → App Server (private)
                                                    → Nginx (port 80)
                                                    → Node.js (port 3000)
```

### Management Flow

```
Jenkins Pipeline
  │
  ├── Terraform Apply
  │     └── Creates: VPC, subnets, IGW, NAT, bastion, ALB, ASG, Route53, SNS
  │
  ├── Python Script (jenkins_awx_deploy.py)
  │     ├── Reads bastion IP from Terraform output
  │     ├── Discovers worker IPs from AWS API (by EC2 tag)
  │     ├── Clears old AWX inventory
  │     ├── Adds fresh worker IPs to app_servers group
  │     ├── Configures bastion as SSH jump host
  │     └── Launches AWX Job Template via REST API
  │
  └── AWX runs Ansible playbook
        ├── SSH path: AWX → Bastion (ec2-user) → Worker (ec2-user)
        ├── Role: security (OS hardening, firewall)
        ├── Role: nodejs (Node.js, PM2, app deployment)
        ├── Role: nginx (reverse proxy)
        ├── Role: monitoring (Prometheus Node Exporter)
        └── Post-task: health check http://localhost:3000
```

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| CI/CD | Jenkins | Pipeline orchestration |
| Infrastructure | Terraform | AWS resource provisioning |
| Configuration | Ansible (AWX) | Server configuration and app deployment |
| Compute | AWS EC2 (ASG) | Auto-scaled application servers |
| Networking | AWS VPC, ALB, NAT, Route 53 | Network isolation, load balancing, DNS |
| Security | Security Groups, Bastion Host | Network access control, SSH jump host |
| Monitoring | Prometheus Node Exporter, SNS | Metrics collection, alerting |
| Application | Node.js, PM2, Nginx | Runtime, process manager, reverse proxy |

---

## Repository Structure

```
├── main.tf                          # VPC, subnets, internet gateway, NAT gateway
├── compute.tf                       # Bastion host EC2, launch template
├── asg.tf                           # Auto Scaling Group for app servers
├── security.tf                      # Security groups: bastion, ALB, app servers
├── loadbalancer.tf                  # ALB, target group, listeners, health checks
├── route53.tf                       # Hosted zone, DNS records
├── sns.tf                           # SNS topic for CloudWatch alerts
├── variables.tf                     # Input variables
├── outputs.tf                       # Terraform outputs (IPs, DNS, URLs)
├── providers.tf                     # AWS provider configuration
├── Jenkinsfile                      # CI/CD pipeline definition
│
├── ansible/
│   ├── playbook.yml                 # Main playbook — runs all 4 roles
│   ├── inventory.py                 # Dynamic inventory script
│   ├── group_vars/
│   │   └── all.yml                  # Global variables (ports, domain, app config)
│   └── roles/
│       ├── security/
│       │   ├── tasks/main.yml       # Firewall, SSH hardening, app user creation
│       │   └── handlers/main.yml    # Service restart handlers
│       ├── nodejs/
│       │   ├── tasks/main.yml       # Node.js install, PM2 setup, app deployment
│       │   └── files/server.js      # Application source code
│       ├── nginx/
│       │   ├── tasks/main.yml       # Nginx install and configuration
│       │   ├── handlers/main.yml    # Nginx restart handler
│       │   └── templates/
│       │       └── nginx.conf.j2    # Nginx config template (reverse proxy)
│       └── monitoring/
│           └── tasks/main.yml       # Prometheus Node Exporter install
│
└── scripts/
    └── jenkins_awx_deploy.py        # Terraform→AWX bridge script
```

---

## Infrastructure Components

### Networking

| Resource | Purpose |
|----------|---------|
| VPC (10.0.0.0/16) | Isolated network for the entire platform |
| Public Subnet AZ1 + AZ2 | Bastion host, ALB, NAT gateway |
| Private Subnet AZ1 + AZ2 | Application servers (no public IPs) |
| Internet Gateway | Inbound traffic to ALB and bastion |
| NAT Gateway | Outbound internet for private subnet (package installs) |
| Route Tables | Public → IGW, Private → NAT |

### Security

| Resource | Inbound Rules |
|----------|--------------|
| Bastion SG | SSH (22) from Jenkins IP + AWX IP |
| ALB SG | HTTP (80) and HTTPS (443) from anywhere |
| App Server SG | SSH (22) from bastion SG only, port 3000 from ALB SG only |

The bastion host is the only SSH entry point into the private subnet.
App servers have no public IPs and accept SSH only from the bastion.
This is the standard bastion/jump-host security pattern.

### Compute

| Resource | Detail |
|----------|--------|
| Bastion Host | t2.micro, public subnet, Elastic IP |
| App Servers | ASG with launch template, private subnet |
| AMI | Amazon Linux 2023 |
| Key Pair | `key` — shared across bastion and workers |

### Load Balancing

| Resource | Detail |
|----------|--------|
| ALB | Application Load Balancer across 2 AZs |
| Target Group | Health check on port 80, routes to app servers |
| Listener | Port 80 → target group |

### DNS and Alerting

| Resource | Detail |
|----------|--------|
| Route 53 | Hosted zone for kaydev.online, A record → ALB |
| SNS | Alert topic for CloudWatch alarms → email notification |

---

## Ansible Roles

### Role: security

Hardens the operating system before any application is installed.

| Task | What it does |
|------|-------------|
| Create application user | Creates `appuser` for running the app (not root) |
| Install firewalld | Installs and enables the firewall |
| Allow SSH (22) | Opens SSH for management access |
| Allow HTTP (80) | Opens HTTP for Nginx |
| Allow app port (3000) | Opens the Node.js application port |
| Allow Node Exporter (9100) | Opens the monitoring metrics port |
| Disable root SSH | Prevents root login via SSH |
| Set SSH idle timeout | Auto-disconnects idle SSH sessions |

### Role: nodejs

Installs Node.js, deploys the application, and configures PM2 process manager.

| Task | What it does |
|------|-------------|
| Install prerequisites | ca-certificates for HTTPS |
| Add NodeSource repo | Adds the official Node.js RPM repository |
| Install Node.js | Installs Node.js 18 from NodeSource |
| Create app directory | /home/appuser/app owned by appuser |
| Copy application | Deploys server.js to the app directory |
| Install PM2 | Global install of PM2 process manager |
| Start app with PM2 | Runs server.js on port 3000 |
| Configure PM2 startup | Ensures the app survives server reboots |

### Role: nginx

Installs Nginx as a reverse proxy in front of the Node.js application.

| Task | What it does |
|------|-------------|
| Install Nginx | Installs Nginx via dnf |
| Deploy config | Templates nginx.conf.j2 with domain and port variables |
| Start and enable | Ensures Nginx is running and starts on boot |

The Nginx template proxies all traffic from port 80 to localhost:3000,
adding proper headers for WebSocket support and client IP forwarding.

### Role: monitoring

Installs Prometheus Node Exporter for infrastructure metrics.

| Task | What it does |
|------|-------------|
| Create service user | node_exporter user with no shell (security) |
| Download binary | Node Exporter v1.7.0 from GitHub releases |
| Install binary | /usr/local/bin/node_exporter |
| Create systemd service | Managed as a system service |
| Start and enable | Running on port 9100, metrics at /metrics |

---

## Jenkins Pipeline

The pipeline supports two modes via a parameter: **deploy** or **destroy**.

### Deploy Mode

```
Install Dependencies → Terraform Apply → AWX Deploy → Verify Deployment
```

| Stage | What it does |
|-------|-------------|
| Install Dependencies | `pip3 install requests` for the AWX API script |
| Terraform Apply | Provisions all AWS infrastructure |
| AWX Deploy | Runs the Python bridge script → triggers Ansible |
| Verify Deployment | Curls the ALB, prints URLs |

### Destroy Mode

```
Terraform Destroy
```

Tears down all AWS resources. One click cleanup.

### Usage

Jenkins → **Build with Parameters** → select `deploy` or `destroy` → **Build**.

---

## AWX Configuration

| Component | Detail |
|-----------|--------|
| Project | Git repo with ansible/ directory |
| Inventory (ID: 3) | `terraform-targets` — dynamically populated by Python script |
| Credential | `Worker_SSH_Key` — Machine type, contains key.pem |
| Job Template (ID: 11) | Combines project + inventory + credential + playbook.yml |

### Dynamic Inventory Flow

The Python script (`scripts/jenkins_awx_deploy.py`) is the bridge between
Terraform and AWX. Static inventory doesn't work here because the ASG
creates instances with new IPs on every deployment.

```
Terraform output → bastion public IP
AWS API query    → worker private IPs (filtered by EC2 tag)
AWX API          → clear old hosts → add new hosts → set SSH jump config → launch job
```

The inventory variables set by the script:

```yaml
ansible_user: ec2-user
ansible_host_key_checking: false
ansible_ssh_common_args: '-o ForwardAgent=yes -o UserKnownHostsFile=/dev/null
  -o StrictHostKeyChecking=no -o ProxyCommand="ssh -o ForwardAgent=yes
  -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null
  -W %h:%p ec2-user@<BASTION_IP>"'
```

This configures the SSH tunnel: AWX → bastion (jump host) → worker (private IP).
`ForwardAgent=yes` passes AWX's loaded SSH key through the tunnel.

---

## Runbooks

### Deploy New Version

```
When:    New application code ready for production
Who:     DevOps engineer
Steps:
  1. Commit code changes to main branch
  2. Jenkins → Build with Parameters → deploy → Build
  3. Monitor Jenkins console: Terraform Apply → AWX Deploy → Verify
  4. Check AWX job output: all tasks green, health check 200
  5. Verify: curl http://<ALB_DNS>
  6. Verify: open http://kaydev.online in browser
```

### Destroy Infrastructure

```
When:    End of demo, cost saving, environment teardown
Who:     DevOps engineer
Steps:
  1. Jenkins → Build with Parameters → destroy → Build
  2. Monitor Jenkins console: Terraform Destroy
  3. Verify in AWS Console: no EC2 instances, no ALB, no NAT gateway
  4. Note: Route 53 hosted zone is destroyed — nameservers will change on rebuild
```

### Rebuild After Destroy

```
When:    Need to bring the environment back up
Who:     DevOps engineer
Steps:
  1. Jenkins → Build with Parameters → deploy → Build
  2. Wait for pipeline to complete (~5-8 minutes)
  3. If domain needed: terraform output nameservers → update in GoDaddy
  4. Verify: curl http://<ALB_DNS>
  5. All infrastructure and configuration is fully automated — no manual steps
```

### SSH into App Servers (Debugging)

```
When:    Need to inspect a running app server
Who:     DevOps engineer
Steps:
  1. Add your laptop IP to bastion security group in AWS Console
  2. Get bastion IP: terraform output bastion_public_ip
  3. SSH to bastion: ssh -i key.pem ec2-user@<BASTION_IP>
  4. From bastion, SSH to worker: ssh ec2-user@<WORKER_PRIVATE_IP>
  5. Check app: pm2 status, curl localhost:3000
  6. Check nginx: systemctl status nginx, curl localhost:80
  7. Check logs: pm2 logs, journalctl -u nginx
```

### Re-run Ansible Only (No Terraform)

```
When:    Configuration change needed, infrastructure already exists
Who:     DevOps engineer
Steps:
  1. AWX UI → Templates → Job Template 11 → Launch
  2. Or: update playbook/roles in Git → AWX syncs project → launch job
  3. Monitor job output in AWX
  4. Verify: health check passes in post_tasks
```

### Rollback Application

```
When:    New deployment broke the application
Who:     DevOps engineer
Steps:
  1. Revert the commit in Git (git revert HEAD)
  2. Push to main
  3. Jenkins → Build with Parameters → deploy
  4. Pipeline re-provisions with the previous code version
  5. Verify: curl http://<ALB_DNS>
  Alternative:
  1. SSH to app server via bastion
  2. pm2 list → identify the running process
  3. Replace server.js with the previous version
  4. pm2 restart my-production
```

### Scaling

```
When:    High traffic, slow response times
Who:     DevOps engineer
Steps:
  1. AWS Console → EC2 → Auto Scaling Groups → select ASG
  2. Edit: increase desired capacity (or adjust scaling policy)
  3. New instances launch automatically in private subnet
  4. ALB health check registers them into the target group
  5. Run AWX job to configure new instances with Ansible
  6. Verify: all instances serving traffic via ALB
```

---

## Pain Points and Lessons Learned

### Bastion username mismatch
The Python script initially used `ubuntu@bastion_ip` but the AMI was
Amazon Linux 2023, which uses `ec2-user`. SSH connections timed out with
cryptic "port 65535" errors. Fix: changed the ProxyCommand to use
`ec2-user`.

### Worker username mismatch
Same issue — `ansible_user: ubuntu` in the inventory variables, but workers
also ran Amazon Linux. Changed to `ansible_user: ec2-user`.

### AWX SSH key not loaded
The AWX Machine credential had an empty SSH Private Key field. AWX attempted
SSH with no key, causing "Permission denied" on every connection. Fix:
uploaded the key.pem contents into the credential.

### ProxyCommand key forwarding
AWX loads the SSH key into an agent, but `ProxyCommand` spawns a separate
SSH process that can't access the agent. Fix: added `-o ForwardAgent=yes`
to both the outer and inner SSH commands.

### Package manager mismatch
Node.js role used `apt` (Ubuntu/Debian) but the servers ran Amazon Linux
(`yum`/`dnf`). Fix: rewrote the role to use `yum` and the NodeSource RPM
repository.

### curl-minimal conflict
Amazon Linux 2023 ships with `curl-minimal`, which conflicts with the full
`curl` package. Fix: removed `curl` from the prerequisite package list
since `curl-minimal` provides the same functionality.

### Bastion security group overwrites
`data.http.my_ip` fetches the IP of whatever machine runs `terraform apply`
(Jenkins), not the developer's laptop. Manually added IPs get overwritten
on the next apply. Fix: added a dedicated ingress rule for the AWX server
IP, and a variable for the developer's laptop IP.

### Route53 nameservers change on rebuild
Every `terraform destroy` + `terraform apply` creates a new hosted zone
with new nameservers, breaking GoDaddy's DNS delegation. In production,
the hosted zone should live outside the ephemeral Terraform state or be
protected with `lifecycle { prevent_destroy = true }`.

---

## Variables Reference

### Terraform Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| project_name | my-production | Resource naming prefix |
| key_name | key | EC2 key pair name |
| domain_name | kaydev.online | Route 53 domain |

### Ansible Variables (group_vars/all.yml)

| Variable | Value | Used by |
|----------|-------|---------|
| app_user | appuser | Security creates user, Node.js runs app as this user |
| app_dir | /home/appuser/app | Node.js deploys code here |
| app_port | 3000 | Node.js listens, Nginx proxies to, health check verifies |
| node_version | 18 | NodeSource repository version |
| nginx_port | 80 | Nginx listens, ALB health check targets |
| project_name | my-production | PM2 process name |
| domain_name | kaydev.online | Nginx server_name directive |

---

## Outputs

| Output | Description |
|--------|------------|
| vpc_id | VPC identifier |
| public_subnet_az1_id | Public subnet in AZ1 |
| public_subnet_az2_id | Public subnet in AZ2 |
| private_subnet_az1_id | Private subnet in AZ1 |
| private_subnet_az2_id | Private subnet in AZ2 |
| bastion_public_ip | Bastion host Elastic IP (SSH entry point) |
| alb_dns_name | ALB DNS (application access) |
| website_url | http://kaydev.online |
| nat_gateway_ip | NAT gateway public IP |
| nameservers | Route 53 nameservers (update in domain registrar) |
| sns_topic_arn | SNS topic for CloudWatch alerts |

