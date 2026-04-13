# Bastion Host
resource "aws_instance" "bastion" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = aws_subnet.public_az1.id
  vpc_security_group_ids = [aws_security_group.bastion.id]

  tags = {
    Name = "${var.project_name}-bastion"
  }
}

# Elastic IP for Bastion
resource "aws_eip" "bastion" {
  instance = aws_instance.bastion.id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-bastion-eip"
  }
}

# Launch Template for App Servers
resource "aws_launch_template" "app" {
  name_prefix   = "${var.project_name}-app-"
  image_id      = var.ami_id
  instance_type = var.instance_type
  key_name      = var.key_name

  network_interfaces {
    associate_public_ip_address = false
    security_groups             = [aws_security_group.app.id]
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    mkdir -p /home/ec2-user/app
    cat > /home/ec2-user/app/index.html << 'HTMLEOF'
    <html>
    <head>
      <title>My Production App</title>
      <style>
        body {
          font-family: Arial, sans-serif;
          background: #1a237e;
          color: white;
          text-align: center;
          padding: 50px;
        }
        h1 { font-size: 2.5em; }
        .info { background: rgba(255,255,255,0.1); padding: 20px; border-radius: 10px; margin: 20px auto; max-width: 600px; }
      </style>
    </head>
    <body>
      <h1>Hello from AWS!</h1>
      <div class="info">
        <p>Deployed by: Anyaragbu Kenechukwu</p>
        <p>Infrastructure provisioned with Terraform</p>
        <p>Configured with Ansible</p>
        <p>Domain: kaydev.online</p>
      </div>
    </body>
    </html>
    HTMLEOF
    cd /home/ec2-user/app
    python3 -m http.server 3000 &
  EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project_name}-app-server"
    }
  }
}