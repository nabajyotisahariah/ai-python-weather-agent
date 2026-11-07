# Google App Engine Deployment Notes

### Step 1 — Prepare the Python Codebase
```bash
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
```

### Step 2: Prerequisites
```bash
1. Install Docker and Docker Compose.
```

### Step 3. Configure the Google Cloud project

```bash
gcloud auth login
gcloud config set project python-workspace-prod
gcloud config get-value project

$ gcloud projects list
PROJECT_ID: weather-project-prod-511603
NAME: weather-project-prod

Configuration requirement:
  The GCP App Engine app.yaml configuration must use the PROJECT_ID defined in the environment variables to configure both:
  - GOOGLE_CLOUD_PROJECT — the target GCP project ID used by the application, including Secret Manager access.
```

### 4. Configure `app.yaml`

```yaml
runtime: python311

entrypoint: uvicorn app.main:app --host 0.0.0.0 --port $PORT

instance_class: F2

automatic_scaling:
  min_instances: 0
  max_instances: 1
  target_cpu_utilization: 0.65
  max_concurrent_requests: 1

env_variables:
  ENVIRONMENT: "production"
  REDIS_ENABLED: "false"
  GOOGLE_CLOUD_PROJECT: "python-workspace-prod"
  DEPLOY_TYPE: "app-engine"
```

## 5. Enable required APIs

```bash
gcloud services enable \
  appengine.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

## 6. Check whether App Engine is already initialized:

```bash
gcloud app describe

ERROR: (gcloud.app.describe) The current Google Cloud project [python-workspace-prod] does not contain an App Engine application. Use `gcloud app create` to initialize an App Engine application within the project
```

## 7. Create the App Engine application

```bash
gcloud app create --region=asia-south1

Creating App Engine application in project [weather-project-prod-511603] and region [asia-south1]....done.                                                   
Success! The app is now created. Please use `gcloud app deploy` to deploy your first app.

IAM [https://console.cloud.google.com/iam-admin/iam]
Principal                                                    Name                                    Role
weather-project-prod-511603@appspot.gserviceaccount.com     App Engine default service account	    Editor

Service accounts [https://console.cloud.google.com/iam-admin/serviceaccounts]
Email                                                        Status                Name
 weather-project-prod-511603@appspot.gserviceaccount.com	    Enabled         App Engine default service account	
```
## 8. Deploy the application

From the root directory of `ai-python-weather-agent`, run:


```bash
$ gcloud app deploy -v=v01
descriptor:                  [/home/nabajyotisahariah009/ai-python-weather-agent/app.yaml]
source:                      [/home/nabajyotisahariah009/ai-python-weather-agent]
target project:              [weather-project-prod-511603]
target service:              [default]
target version:              [v01]
target url:                  [https://weather-project-prod-511603.el.r.appspot.com]
target service account:      [weather-project-prod-511603@appspot.gserviceaccount.com]
                                 
Deployed service [default] to [https://weather-project-prod-511603.el.r.appspot.com]

You can stream logs from the command line by running:
  $ gcloud app logs tail -s default

It will create below services & storage folders
https://console.cloud.google.com/iam-admin/iam
Principal                                                 Name                                    Role
python-workspace-prod@appspot.gserviceaccount.com       App Engine default service account	    Editor

https://console.cloud.google.com/iam-admin/serviceaccounts
Email                                                     Status                   
python-workspace-prod@appspot.gserviceaccount.com	      Enabled                   App Engine default service 

https://console.cloud.google.com/storage/browser
staging.weather-project-prod-511603.appspot.com
weather-project-prod-511603.appspot.com

```

### 9. Application logs
    
  ```bash
    Cloud Build 
          History 
              https://console.cloud.google.com/cloud-build/builds

    Logs Explorer
          https://console.cloud.google.com/logs/query
  ```

### 10. Debugging Application Failure on 'Logs Explorer'

  1. Bucket permission issue during deployment
    Grant the required storage permission:
  ```bash
  gcloud storage buckets add-iam-policy-binding \
  gs://staging.weather-project-prod-511603.appspot.com \
  --member="weather-project-prod-511603@appspot.gserviceaccount.com" \
  --role="roles/storage.admin"
  ```

  2. Service due to permission issue
  google.api_core.exceptions.PermissionDenied: 403 Permission 'secretmanager.versions.access' denied on resource (or it may not exist). Remediate access with this Troubleshooter URL or share it with your administrator - https://console.cloud.google.com/iam- 

  3. ERROR: failed to initialize analyzer: validating registry read access:: Permission 'artifactregistry.repositories.downloadArtifacts'

### 11. Artifact Registry / Logging / Secret Manager permissions

> Grant the required IAM roles:

```bash
PROJECT_ID="weather-project-prod-511603"
SERVICE_ACCOUNT="${PROJECT_ID}@appspot.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/artifactregistry.createOnPushWriter"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/artifactregistry.reader"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```
> Or we can add manually below permission on the Service Account
  ```bash
  1. Artifact Registry Create-on-Push Writer
  2. Artifact Registry Reader
  3. Logs Writer
  4. Secret Manager Secret Accessor
  ```

> GCP IAM Role Update
  ```bash
https://console.cloud.google.com/iam-admin/iam
 Principal: weather-project-prod-511603@appspot.gserviceaccount.com   
 Name     : App Engine default service account	
 Role     : Artifact Registry Create-on-Push Writer
            Artifact Registry Reader
            Editor
            Logs Writer
            Secret Manager Secret Accessor
```

> In App Engine, this service account is configured under: App Engine > Dashboard > Settings > Application Settings > Default service account

### 12. Add secrets to Secret Manager

### Create secrets & update the keys version wise from the GCP Console UI 

```bash
echo -n "YOUR_OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
echo -n "YOUR_LANGFUSE_PUBLIC_KEY" | gcloud secrets create LANGFUSE_PUBLIC_KEY --data-file=-
echo -n "YOUR_LANGFUSE_SECRET_KEY" | gcloud secrets create LANGFUSE_SECRET_KEY --data-file=-
```

### 13. Application changes required

App Engine Standard does not support the same `--set-secrets` mapping flow used by Cloud Run.

For the weather agent on App Engine, the practical options are:

- Option 1 (recommended): Load secrets at runtime through the Secret Manager Python client.
- Option 2: Use App Engine Flexible with a custom container and retrieve secrets during startup.

This is different from the native Cloud Run pattern where secret values can be mapped directly as environment variables.

### 14. Deployed endpoints

 App Engine
  ```text
  
  https://weather-project-prod-511603.el.r.appspot.com/api/v1/health
  {"status":"ok"}

  https://weather-project-prod-511603.el.r.appspot.com/api/v1/weather/langgraph?city=what is the weather of delhi
  {"status":"success","message":"The current weather in Delhi is as follows:\n- **Temperature:** 28°C\n- **Feels Like:** 28°C\n- **Humidity:** 53%\n- **Weather Condition:** Smoky haze\n- **Wind Speed:** 9 km/h","isCached":false}


  curl --location 'https://weather-project-prod-511603.el.r.appspot.com/api/v1/weather/agent' \
--header 'Content-Type: application/json' \
--data '{"query": "What is the current weather in Delhi, and what is the forecast for the upcoming days?"}'
  {
    "status": "success",
    "message": "The current weather in Delhi is as follows:\n- Temperature: 28°C\n- Feels-like Temperature: 28°C\n- Humidity: 53%\n- Weather Condition: Smoky haze\n- Wind Speed: 9 km/h\n\nHere is the weather forecast report for Delhi for the upcoming days:\n- Date: 14th October 2026, Max Temp: 34°C, Min Temp: 26°C, Weather Condition: Sunny\n- Date: 15th October 2026, Max Temp: 35°C, Min Temp: 26°C, Weather Condition: Cloudy\n- Date: 16th October 2026, Max Temp: 33°C, Min Temp: 25°C, Weather Condition: Sunny\n\nThis provides you with the current weather and the forecast for the next three days in Delhi.",
    "isCached": false
}
  ```

   Cloud Run
  ```text
    https://app-ai-python-weather-513793705540.asia-south2.run.app/
  ```

### 15. Traffic Control using 'ingress setting'
```bash
    Allow All Traffic
    Allow internal traffic and traffic from Cloud Load Balancing
    Allow internal traffic only
```

## 16. App Engine vs Cloud Run vs GKE

| Capability | App Engine Standard | Cloud Run | GKE |
| --- | --- | --- | --- |
| Infrastructure management | Minimal | Minimal | More operational work |
| Custom Docker image | No | Yes | Yes |
| Kubernetes control | No | No | Yes |
| Autoscaling | Yes | Yes | Configurable |
| Best fit | Managed Python web API | Containerized FastAPI and AI agents | Complex multi-service platform |
