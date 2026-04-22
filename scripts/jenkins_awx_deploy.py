import os
import json
import subprocess
import requests

AWX_URL = os.environ['AWX_URL']
AWX_TOKEN = os.environ['AWX_TOKEN']
INVENTORY_ID = os.environ['INVENTORY_ID']
JOB_TEMPLATE_ID = os.environ['JOB_TEMPLATE_ID']

HEADERS = {
    "Authorization": f"Bearer {AWX_TOKEN}",
    "Content-Type": "application/json"
}

def run(cmd):
    return subprocess.check_output(cmd, shell=True).decode()

# 1. Get terraform outputs
run("terraform output -json > tf.json")

with open("tf.json") as f:
    data = json.load(f)

bastion_ip = data["bastion_public_ip"]["value"]

# 2. Get EC2 private IPs from AWS
ips = json.loads(run("""
aws ec2 describe-instances \
--filters Name=tag:Name,Values=my-production-app-server Name=instance-state-name,Values=running \
--query 'Reservations[].Instances[].PrivateIpAddress' \
--output json
"""))

print("EC2 IPs:", ips)

# 3. Clear AWX hosts
hosts = requests.get(f"{AWX_URL}/api/v2/inventories/{INVENTORY_ID}/hosts/", headers=HEADERS).json()

for h in hosts['results']:
    requests.delete(f"{AWX_URL}/api/v2/hosts/{h['id']}/", headers=HEADERS)

# 4. Ensure group exists
groups = requests.get(f"{AWX_URL}/api/v2/inventories/{INVENTORY_ID}/groups/", headers=HEADERS).json()
group_id = None

for g in groups['results']:
    if g['name'] == "app_servers":
        group_id = g['id']

if not group_id:
    r = requests.post(f"{AWX_URL}/api/v2/inventories/{INVENTORY_ID}/groups/",
                      headers=HEADERS,
                      json={"name": "app_servers"})
    group_id = r.json()['id']

# 5. Update inventory vars (bastion SSH)
requests.patch(
    f"{AWX_URL}/api/v2/inventories/{INVENTORY_ID}/",
    headers=HEADERS,
    json={
        "variables": f"""
ansible_user: ubuntu
ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o ProxyCommand="ssh -o StrictHostKeyChecking=no -W %h:%p -q ubuntu@{bastion_ip}"'
"""
    }
)

# 6. Add hosts
for ip in ips:
    r = requests.post(
        f"{AWX_URL}/api/v2/hosts/",
        headers=HEADERS,
        json={"name": ip, "inventory": int(INVENTORY_ID)}
    )
    host_id = r.json()['id']

    requests.post(
        f"{AWX_URL}/api/v2/groups/{group_id}/hosts/",
        headers=HEADERS,
        json={"id": host_id}
    )

print("AWX inventory updated")

# 7. Launch job
r = requests.post(
    f"{AWX_URL}/api/v2/job_templates/{JOB_TEMPLATE_ID}/launch/",
    headers=HEADERS
)

job_id = r.json()['job']
print("Launched job:", job_id)
