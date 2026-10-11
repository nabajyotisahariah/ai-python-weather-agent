### Step 1 - Create a Redis instance using Memorystore
The following example uses your Weather Agent's GCP project, python-project-1st-sep, and the Delhi region, asia-south2. The Redis instance must be in a VPC that your GKE cluster can reach. 

Step 1 — Enable the Redis API

```bash
gcloud config set project PROJECT_ID

gcloud services enable redis.googleapis.com
```

### Step 2 — Create a Redis instance
For a basic development or testing setup:

```bash
$ gcloud redis instances create redis-cluster \
  --size=1 \
  --region=asia-south2 \
  --tier=basic \
  --redis-version=redis_7_0 \
  --network=default

Create request issued for: [redis-cluster]
Waiting for operation [projects/PROJECT_ID/locations/asia-south2/
operations/operation-1791707084028-65d8c5048f9be-d462066f-370e8bc3] to complete
...done.                                                                       
Created instance [redis-cluster].
```

Important:
- This example assumes your GKE cluster uses the default VPC. Replace it with the actual VPC if necessary.
- Basic Tier is suitable for experimentation, but it does not provide the same high availability as Standard Tier.
- Memorystore is a billed service, even when your application is not using it.


### Step 3 — Retrieve the Redis IP address
```bash
$ gcloud redis instances describe redis-cluster \
  --region=asia-south2 \
  --format="yaml(host,port,authorizedNetwork)"
authorizedNetwork: projects/PROJECT_ID/global/networks/default
host: XXX.XXX.XXX.XXX
port: 6379
```

### Step 4 Check Redis from your terminal
```bash
redis-cli -h XXX.XXX.XXX.XXX -p 6379 PING
PONG

sudo apt update
sudo apt install -y redis-tools
```

### Step 5 - Integrate Redis with your FastAPI Weather Agent
```bash
Install the Python Redis client:
pip install redis
```
