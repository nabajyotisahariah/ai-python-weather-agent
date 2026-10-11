
### Step 1 — Prepare Your Python Application
app/
├── agents/              # CrewAI, LangGraph, AutoGen, and Google ADK agents
├── orchestrator/        # CrewAI multi-agent orchestrator
├── route/               # FastAPI route handlers
├── schema/              # Pydantic request and response models
├── services/            # Weather service and service interface
├── tools/               # Agent weather tools
├── config.py            # Environment-backed settings
├── main.py              # FastAPI application
├── weather-mcp.py       # FastMCP server configuration
└── utils/               # Logging and Redis cache helpers
data/                    # Data directory for vector DB, FAQ documents, and prompts
script/                  # Helper and test scripts (e.g., FAISS index builder)
helm-config/             # Kubernetes Helm chart for Application
helm-mcp/                # Kubernetes Helm chart for FastMCP
tests/                   # API and service tests

### Step 2: Prerequisites

1. Install Docker and Docker Compose.

### Step 3 — Create / Select GCP Project

1. Created new Project on GCP
    project-workspace

2. GCP Project list 
    $ gcloud projects list
    PROJECT_ID                  NAME                        PROJECT_NUMBER  ENVIRONMENT
    python-project-1st-sep      Python Project 1st Sep      1040682241529

3. Sync gcloud
    $ gcloud auth login
    Your current project is [XYZ Project].  You can change this setting by running:
    $ gcloud config set project PROJECT_ID

    $ gcloud projects list
    PROJECT_ID                  NAME                        PROJECT_NUMBER  ENVIRONMENT
    project-workspace-511112    project-workspace           426899950764
    python-project-1st-sep      Python Project 1st Sep      1040682241529

4. Set your project:
    $ gcloud config set project project-workspace-511112

    To update your Application Default Credentials quota project, use the `gcloud auth application-default set-quota-project` command.
    Updated property [core/project].

    $ gcloud auth application-default set-quota-project project-workspace-511112

    --------------
    $ gcloud config set project project-workspace-511112
    Updated property [core/project].

    Verify:

    ```bash
    $ gcloud config get-value project
    project-workspace-511112

    ```

### 4 Set variables:

```bash
#asia-south2-docker.pkg.dev/project-workspace-511112/artifact-ai-python-weather-agent
export PROJECT_ID=$(gcloud config get-value project)
export REGION=asia-south2
export SERVICE=app4-ai-python-weather
export SERVICE_ACCOUNT=service4-ai-python-weather
export REPOSITORY=artifact4-ai-python-weather-agent
export IMAGE=ai4-python-weather-agent
export TAG=1.1

Note: 
    $ gcloud config get-value project 
    project-workspace-511112

    $ echo "$PROJECT_ID"
    project-workspace-511112
```

### Step 5 — Enable Required APIs for cloudbuild & secretmanager in the Project

For your application:

```bash
$ gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com

$ gcloud services list --enabled
NAME                                 TITLE
cloudbuild.googleapis.com            Cloud Build API
run.googleapis.com                   Cloud Run Admin API
secretmanager.googleapis.com         Secret Manager API
```


### Step 6 — Create Artifact Registry to store the docker images [https://console.cloud.google.com/artifacts]

Create a Docker repository:

```bash
$ gcloud artifacts repositories create $REPOSITORY \
  --repository-format=docker \
  --location=asia-south2 \
  --description="AI Weather Agent Docker Repository"

  Create request issued for: [artifact-ai-python-weather-agent]
  Created repository 
```

Verify:

```bash
gcloud artifacts repositories list \
  --location=asia-south2

REPOSITORY                        FORMAT  MODE                 DESCRIPTION  
artifact-ai-python-weather-agent  DOCKER  STANDARD_REPOSITORY  AI Weather Agent Docker Repository

```

### Step 7 — Authenticate Docker, this allows Docker to push images to Artifact Registry.

```bash
$ gcloud auth configure-docker asia-south2-docker.pkg.dev

Adding credentials for: asia-south2-docker.pkg.dev
Docker configuration file updated.
```


### Step 8 — Build Docker Image locally or VM

```
Build:

```bash
docker build -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG .
docker build --no-cache -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG .
```

Check:

```bash
$ docker images

IMAGE                                                            ID             
asia-south2-docker.pkg.dev/project-workspace-511112/artifact-ai-python-weather-agent/ai-python-weather-agent:1.0
```

### Step 9 — Test Locally

Run:

```bash
$ docker run -p 8000:8000 $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG

ERROR: .env file is not present: /app/.env  #Error for security reason, as .env is not saved in the git repo
```


### Step 10 — Push Image to Artifact Registry  [https://console.cloud.google.com/artifacts]

```bash
docker push $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG
```

Verify:

```bash
gcloud artifacts docker images list $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY
```

### Step 10 — Create Secret Manager Secrets [https://console.cloud.google.com/security/secret-manager/secrets]

Don't deploy your `.env` file.

- Create secrets:

```bash
$ echo -n "production" | gcloud secrets create ENVIRONMENT --data-file=-
$ echo -n "YOUR_OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
$ echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
$ echo -n "YOUR_LANGFUSE_PUBLIC_KEY" | gcloud secrets create LANGFUSE_PUBLIC_KEY --data-file=-
$ echo -n "YOUR_LANGFUSE_SECRET_KEY" | gcloud secrets create LANGFUSE_SECRET_KEY --data-file=-
$ echo -n "REDIS_URL" | gcloud secrets create REDIS_URL   --data-file=-
Created version [1] of the secret [REDIS_URL].
```

You can verify:

```bash
$ gcloud secrets list

NAME                 CREATED              REPLICATION_POLICY  LOCATIONS
ENVIRONMENT          2026-10-09T14:06:21  automatic           -
GOOGLE_API_KEY       2026-10-09T14:06:21  automatic           -
LANGFUSE_PUBLIC_KEY  2026-10-09T14:00:50  automatic           -
```

### Step 12 — Create the service account [https://console.cloud.google.com/iam-admin/serviceaccounts]

Instead of using broad permissions, create a dedicated service account:

```bash
$ gcloud iam service-accounts create $SERVICE_ACCOUNT --display-name="AI Weather Agent Service"

Created service account [service-ai-python-weather].
```

### Step 13 - Grant Secret Manager access: [https://console.cloud.google.com/iam-admin/iam]
  For better security, grant access only to the specific secret the application needs. For example, to allow access to the openai-api-key secre. It will create an entry IAM services for the SERVICE_ACCOUNT service. It will create a new record in IM Service wth the $SERVICE_ACCOUNT

```bash
$ gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

  -----
  Updated IAM policy for project [project-workspace-511112].
  bindings:
    role: roles/secretmanager.secretAccessor
  version: 1  
```

### Step 14 — Deploy to Cloud  [https://console.cloud.google.com/run/overview]

Now deploy your Docker image:

```bash
gcloud run deploy "$SERVICE" \
  --image="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:${TAG}" \
  --region=asia-south2 \
  --platform=managed \
  --service-account="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
  --port=8000 \
  --memory=1Gi \
  --cpu=1 \
  --min=0 \
  --max-instances=1 \
  --set-env-vars="ENVIRONMENT=production" \
  --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,REDIS_URL=REDIS_URL:latest,LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest,LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest" \
  --allow-unauthenticated
```

  On Error
  Permission 'iam.serviceaccounts.actAs' denied on service account $SERVICE_ACCOUNT

  $ gcloud iam service-accounts add-iam-policy-binding \
    "${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --project="$PROJECT_ID" \
    --member="user:nabajyotisahariah009@gmail.com" \
    --role="roles/iam.serviceAccountUser"

  Updated IAM policy for serviceAccount [service1-ai-python-weather@project-workspace-511112.iam.gserviceaccount.com].
  bindings:
  - members:
    - user:nabajyotisahariah009@gmail.com
    role: roles/iam.serviceAccountUser
  etag: BwZdhtWnsZk=
  version: 1


### Step 15 — Configure Secrets in Cloud Run [https://console.cloud.google.com/run/overview]

You can bind Secret Manager secrets directly to environment variables:

```bash
$ gcloud run services update $SERVICE \
  --region=$REGION \
  --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest,LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest"

OK Deploying... Done.
OK Creating Revision...
OK Routing traffic...
Done.
Service URL: https://ai-python-weather-agent-426899950764.asia-south2.run.app
```

### Step 16 — Configure Environment Variables

For non-sensitive configuration:

```bash
gcloud run services update $SERVICE \
  --region=$REGION \
  --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO"
```

For example:

```text
ENVIRONMENT=production
LOG_LEVEL=INFO
MODEL=gpt-4o-mini
CACHE_TTL=3600
```

Keep credentials in **Secret Manager**, not environment variables stored directly in deployment scripts.

---

### Step 17 — Configure Scaling

For your weather API:

```bash
gcloud run services update $SERVICE \
  --region=$REGION \
  --min=0 \
  --max=10
```

### Step 18 — Make the Service Public

If this is a public demo API:

```bash
gcloud run services add-iam-policy-binding $SERVICE \
  --region=$REGION \
  --member="allUsers" \
  --role="roles/run.invoker"
```

Now your API can be accessed publicly.

For production, however, don't automatically make the service public. Prefer authentication/API gateway or another appropriate access-control layer.

---

### Step 19 — Test Your Cloud Run API

Get the URL:

```bash
gcloud run services describe $SERVICE \
  --region=$REGION \
  --format="value(status.url)"
```

For your forecast endpoint:

```bash
curl "https://YOUR-CLOUD-RUN-URL/api/v1/weather/forecast/crewai?city=Chicago"
```

### Step 20 — Check Logs

1. Cloud Run logs:

```bash
gcloud run services logs read $SERVICE --region=$REGION
gcloud run services logs read "$SERVICE" --region="$REGION" --limit=100

2026-10-09  - app.utils.logger - INFO - Logging configured successfully.
2026-10-09  - root - INFO - Starting Weather Assistant API production
2026-10-09  - root - INFO - Initializing API routes
2026-10-09  - root - INFO - Environment: production
2026-10-09  - root - INFO - OpenAI Model: gpt-4o-mini

```

2. Stream live logs continuously
gcloud beta run services logs tail "$SERVICE" \
  --region="$REGION"

### Step 21 — Create a New Version

When you change the application:

```bash
export TAG=1.1
```

Build:

```bash
docker build \
  -t $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG .
```

Push:

```bash
docker push \
  $REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG
```

Deploy:

```bash
gcloud run deploy $SERVICE \
  --image=$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/$IMAGE:$TAG \
  --region=$REGION
```
### Run the Deployment Script

Step 1 — Check the prerequisites
  Run these commands in the same terminal:
  gcloud --version
  docker --version
  docker info
  gcloud auth list
  gcloud config get-value project

Step 2 — Fix the permissions
  Run:
    chmod +x deploy.sh

Step 3 : Run the pipelie
  ./deploy.sh production