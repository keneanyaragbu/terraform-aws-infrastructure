import os
import json
import subprocess
import requests
import sys

AWX_URL = os.environ['AWX_URL'].rstrip("/")
AWX_TOKEN = os.environ['AWX_TOKEN']
INVENTORY_ID = os.environ['INVENTORY_ID']
JOB_TEMPLATE_ID = os.environ['JOB_TEMPLATE_ID']

HEADERS = {
    "Authorization": f"Bearer {AWX_TOKEN}",
    "Content-Type": "application/json"
}

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True)

def awx_get(path):
    url = f"{AWX_URL}{path}"
    r = requests.get(url, headers=HEADERS, timeout=30)
    print(f"GET {url} -> {r.status_code}")
    print(r.text)
    r.raise_for_status()
    return r.json()

def awx_post(path, payload=None):
    url = f"{AWX_URL}{path}"
    r = requests.post(url, headers=HEADERS, json=payload or {}, timeout=30)
    print(f"POST {url} -> {r.status_code}")
    print(r.text)
    r.raise_for_status()
    return r.json()

def awx_delete(path):
    url = f"{AWX_URL}{path}"
    r = requests.delete(url, headers=HEADERS, timeout=30)
    print(f"DELETE {url} -> {r.status_code}")
    print(r.text)
    r.raise_for_status()

def awx_patch(path, payload):
    url = f"{AWX_URL}{path}"
    r = requests.patch(url, headers=HEADERS, json=payload, timeout=30)
    print(f"PATCH {url} -> {r.status_code}")
    print(r.text)
    r.raise_for_status()
    return r.json()

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

# 3. Fetch inventory hosts safely
hosts_resp = awx_get(f"/api/v2/inventories/{INVENTORY_ID}/hosts/")

if "results" not in hosts_resp:
    print("Unexpected AWX response for inventory hosts endpoint")
    sys.exit(1)

for h in hosts_resp["results"]:
    awx_delete(f"/api/v2/hosts/{h['id']}/")

# 4. Ensure group exists
groups_resp = awx_get(f"/api/v2/inventories/{INVENTORY_ID}/groups/")

if "results" not in groups_resp:
    print("Unexpected AWX response for inventory groups endpoint")
    sys.exit(1)

group_id = None
for g in groups_resp["results"]:
    if g["name"] == "app_servers":
        group_id = g["id"]
        break

if not group_id:
    new_group = awx_post(
        f"/api/v2/inventories/{INVENTORY_ID}/groups/",
        {"name": "app_servers"}
    )
    group_id = new_group["id"]

# 5. Update inventory vars
awx_patch(
    f"/api/v2/inventories/{INVENTORY_ID}/",
    {
        "variables": f"""ansible_user: ubuntu
ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o ProxyCommand="ssh -o StrictHostKeyChecking=no -W %h:%p -q ubuntu@{bastion_ip}"'
"""
    }
)

# 6. Add hosts
for ip in ips:
    host = awx_post(
        "/api/v2/hosts/",
        {"name": ip, "inventory": int(INVENTORY_ID)}
    )
    host_id = host["id"]

    awx_post(
        f"/api/v2/groups/{group_id}/hosts/",
        {"id": host_id}
    )

print("AWX inventory updated")

# 7. Launch job
launch = awx_post(
    f"/api/v2/job_templates/{JOB_TEMPLATE_ID}/launch/",
    {}
)

print("Launch response:", launch)

job_id = launch.get("job")
if not job_id:
    print("No job ID returned from launch response")
    sys.exit(1)

print("Launched job:", job_id)