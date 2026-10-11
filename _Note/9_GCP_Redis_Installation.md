### Step 1 - Create a Redis instance using Memorystore
The following example uses your Weather Agent's GCP project, python-project-1st-sep, and the Delhi region, asia-south2. The Redis instance must be in a VPC that your GKE cluster can reach. 

Step 1 — Enable the Redis API
gcloud config set project PROJECT_ID

gcloud services enable redis.googleapis.com

### Step 2 — Create a Redis instance
For a basic development or testing setup:

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

Important:
- This example assumes your GKE cluster uses the default VPC. Replace it with the actual VPC if necessary.
- Basic Tier is suitable for experimentation, but it does not provide the same high availability as Standard Tier.
- Memorystore is a billed service, even when your application is not using it.


### Step 3 — Retrieve the Redis IP address

nabajyotisahariah009@ec2-python:~$ gcloud redis instances describe redis-cluster \
  --region=asia-south2 \
  --format="yaml(host,port,authorizedNetwork)"
authorizedNetwork: projects/PROJECT_ID/global/networks/default
host: XXX.XXX.XXX.XXX
port: 6379

### Step 4 Check Redis from your terminal

redis-cli -h XXX.XXX.XXX.XXX -p 6379 PING
PONG

sudo apt update
sudo apt install -y redis-tools

### Step 5 - Integrate Redis with your FastAPI Weather Agent
Install the Python Redis client:
pip install redis


==========
The traceback confirms that your Python application is timing out while opening a TCP connection to Redis. The failure occurs before Redis can respond to `PING`.

Your Memorystore instance is `READY`, with endpoint `100.142.185.171:6379`. So the first thing to investigate is private network connectivity, not the Redis URL syntax.

## 1. Confirm where the application is running

Your earlier terminal showed an EC2 machine, but the logs look like they may come from a container deployed on Cloud Run. These environments require different networking configurations.

- Cloud Run: needs configured private VPC connectivity to reach Memorystore.
- AWS EC2: cannot normally reach a private GCP IP address directly without cross-cloud network connectivity.
- GKE: needs compatible VPC connectivity and routing to the Memorystore instance.

## 2. Check the Cloud Run network configuration

Run these commands for the service producing the error:

```
gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format="yaml(spec.template.metadata.annotations,spec.template.spec.containers)"
```

Look for the configured VPC network, subnet, or Serverless VPC Access connector.

Your Memorystore instance is in project `project-workspace-511112`, on the `default` network. If Cloud Run is in `python-project-1st-sep`, verify that it has a valid route to that exact network. Two VPCs both named `default` are not necessarily the same network.

## 3. Test TCP connectivity from Cloud Run

Temporarily add this diagnostic to your Python application:

```
import socketimport logginglogger = logging.getLogger(__name__)def test_redis_tcp():    try:        with socket.create_connection(            ("10.142.185.179", 6379),            timeout=5,        ):            logger.info("Redis TCP connection successful")    except OSError:        logger.exception("Redis TCP connection failed")
```

Call `test_redis_tcp()` during a controlled diagnostic run.

- If it times out, investigate VPC connectivity and routing.
- If TCP connects but `redis_client.ping()` fails, investigate Redis protocol, authentication, or TLS settings.

## 4. Check the Cloud Run configuration and Memorystore network

Confirm the Redis instance details:

```
gcloud redis instances describe redis-cluster \
  --project=project-workspace-511112 \
  --region=asia-south2 \
  --format="yaml(host,port,state,authorizedNetwork,connectMode)"
```

For the Cloud Run service, configure Direct VPC egress or a Serverless VPC Access connector that can reach the Memorystore network. If the service and Redis instance are in different projects, cross-project VPC connectivity must also be established.

Google's guide: [Connect Cloud Run to a VPC network](https://cloud.google.com/run/docs/configuring/connecting-vpc).

Please share the output of this command (you can redact unrelated details):

```
gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format="yaml(spec.template.metadata.annotations)"
```
====

Your output identifies the likely cause: the Cloud Run service has no visible VPC connectivity configuration in the annotations you shared, while Memorystore uses Direct Peering on the `default` VPC in project `project-workspace-511112`.

The Redis endpoint itself is healthy:

- Host: `10.142.185.179`
- Port: `6379`
- State: `READY`
- Network: `projects/project-workspace-511112/global/networks/default`

The annotation output alone doesn't prove that no VPC connectivity exists, because some network settings can be represented elsewhere in the service configuration. Let's verify the project and network before changing anything.

## 1. Check which project hosts Cloud Run

Run:

```
echo "Current project: $(gcloud config get-value project)"
echo "Cloud Run project: $PROJECT_ID"
echo "Cloud Run region: $REGION"
echo "Cloud Run service: $SERVICE"
```

If the Cloud Run service is in `project-workspace-511112`, continue with the configuration below.

## 2. Enable Direct VPC egress

First, verify that the `default` subnet exists in the Cloud Run region:

```
gcloud compute networks subnets list \
  --project=project-workspace-511112 \
  --filter="network:default AND region:asia-south2"
```

If the subnet exists and the Cloud Run service uses the same VPC as Memorystore, configure the service:

```
gcloud run services update "$SERVICE" \
  --project=project-workspace-511112 \
  --region="$REGION" \
  --network=default \
  --subnet=default \
  --vpc-egress=private-ranges-only
```

This enables private VPC egress without requiring a Serverless VPC Access connector.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://docs.cloud.google.com\&sz=32)

Google Cloud Documentation

+1



## 3. Verify and test

Check the updated service configuration:

```
gcloud run services describe "$SERVICE" \
  --project=project-workspace-511112 \
  --region="$REGION"
```

Then trigger your health endpoint and review the latest logs:

```
gcloud run services logs read "$SERVICE" \
  --project=project-workspace-511112 \
  --region="$REGION" \
  --limit=50
```

You want to see `Redis connection successful` instead of a connection timeout.

Before running the update: If `$PROJECT_ID` is different from `project-workspace-511112`, don't apply the command blindly. Tell me the Cloud Run project ID. We need to establish access to the Memorystore VPC in the correct project first.