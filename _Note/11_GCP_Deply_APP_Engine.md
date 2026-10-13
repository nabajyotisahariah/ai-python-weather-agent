# Google App Engine Deployment Notes

## 1. Configure the Google Cloud project

```bash
gcloud auth login
gcloud config set project python-workspace-511515
gcloud config get-value project
```

## 2. Enable required APIs

```bash
gcloud services enable \
  appengine.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com
```

Check whether App Engine is already initialized:

```bash
gcloud app describe
```

## 3. Create the App Engine application

```bash
gcloud app create --region=asia-south1
```

> The App Engine region cannot be changed after creation.

## 4. Deploy the application

From the root directory of `ai-python-weather-agent`, run:


```bash
$ gcloud app deploy -v=v01
Services to deploy:

descriptor:                  [/home/local/ai-python-weather-agent/app.yaml]
source:                      [/home/local/ai-python-weather-agent]
target project:              [python-workspace-511515]
target service:              [default]
target version:              [v01]
target url:                  [https://python-workspace-511515.el.r.appspot.com]
target service account:      [service-app-engine-demo@python-workspace-511515.iam.gserviceaccount.com]

done.                                                                                                          
Deployed service [default] to [https://python-workspace-511515.el.r.appspot.com]

You can stream logs from the command line by running:
  $ gcloud app logs tail -s default

It will create below services & storage folders
https://console.cloud.google.com/iam-admin/iam
Principal                                                 Name                                    Role
python-workspace-511515@appspot.gserviceaccount.com       App Engine default service account	    Editor

https://console.cloud.google.com/iam-admin/serviceaccounts
Email                                                     Status                    python-workspace-511515@appspot.gserviceaccount.com	  Enabled                   App Engine default service 

https://console.cloud.google.com/storage/browser
staging.python-workspace-511515.appspot.com - 
python-workspace-511515.appspot.com

```

## 5. Bucket permission issue during deployment

If you see an error like:

```bash
invalid bucket "staging.python-workspace-511515.appspot.com";
service account service-app-engine-demo@python-workspace-511515.iam.gserviceaccount.com does not have access to the bucket
```

Grant the required storage permission:

```bash
gcloud storage buckets add-iam-policy-binding \
  gs://staging.python-workspace-511515.appspot.com \
  --member="serviceAccount:service-app-engine-demo@python-workspace-511515.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
```

You can verify the service account and roles in the Google Cloud Console:

- IAM & Admin > IAM
- Service account: `service-app-engine-demo@python-workspace-511515.iam.gserviceaccount.com`

## 6. Artifact Registry / Logging / Secret Manager permissions

If deployment fails with errors such as:

```bash
ERROR: failed to initialize analyzer: validating registry read access:: Permission 'artifactregistry.repositories.downloadArtifacts'
```

Grant the required IAM roles:

```bash
PROJECT_ID="python-workspace-511515"
SERVICE_ACCOUNT="service-app-engine-demo@${PROJECT_ID}.iam.gserviceaccount.com"

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
Or we can add manually below permission on the Service Account
# 1. Artifact Registry Create-on-Push Writer
# 2. Artifact Registry Reader
# 3. Logs Writer
# 4. Secret Manager Secret Accessor

> In App Engine, this service account is configured under: App Engine > Dashboard > Settings > Application Settings > Default service account

## 7. Add secrets to Secret Manager

### Create secrets

```bash
echo -n "YOUR_OPENAI_KEY" | gcloud secrets create OPENAI_API_KEY --data-file=-
echo -n "YOUR_GOOGLE_API_KEY" | gcloud secrets create GOOGLE_API_KEY --data-file=-
echo -n "YOUR_LANGFUSE_PUBLIC_KEY" | gcloud secrets create LANGFUSE_PUBLIC_KEY --data-file=-
echo -n "YOUR_LANGFUSE_SECRET_KEY" | gcloud secrets create LANGFUSE_SECRET_KEY --data-file=-
```

### Enable Secret Manager API

```bash
gcloud services enable secretmanager.googleapis.com --project=python-workspace-511515
```

### Grant access to the App Engine runtime service account

```bash
PROJECT_ID="python-workspace-511515"
RUNTIME_SA="service-app-engine-demo@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
  --project=python-workspace-511515 \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="roles/secretmanager.secretAccessor"
```

Repeat the same pattern for each required secret as needed.

## 8. Configure `app.yaml`

```yaml
runtime: python311

entrypoint: uvicorn app.main:app --host 0.0.0.0 --port $PORT

service_account: service-app-engine-demo@python-workspace-511515.iam.gserviceaccount.com

instance_class: F2

automatic_scaling:
  min_instances: 0
  max_instances: 1
  target_cpu_utilization: 0.65
  max_concurrent_requests: 1

env_variables:
  ENVIRONMENT: "production"
  REDIS_ENABLED: "false"
  GOOGLE_CLOUD_PROJECT: "python-workspace-511515"
  DEPLOY_TYPE: "app-engine"
```

## 9. Application changes required

App Engine Standard does not support the same `--set-secrets` mapping flow used by Cloud Run.

For the weather agent on App Engine, the practical options are:

- Option 1 (recommended): Load secrets at runtime through the Secret Manager Python client.
- Option 2: Use App Engine Flexible with a custom container and retrieve secrets during startup.

This is different from the native Cloud Run pattern where secret values can be mapped directly as environment variables.

## 10. Debugging on GCP

Use:

- Logs Explorer
- Cloud Run service logs
- App Engine logs

to inspect startup failures, secret access errors, runtime exceptions, and deployment warnings.

## 11. Deployed endpoints

### App Engine

```text
https://python-workspace-511515.el.r.appspot.com/api/v1/weather/langgraph?city=delhi
https://python-workspace-511515.el.r.appspot.com/api/v1/health
```

### Cloud Run

```text
https://app-ai-python-weather-513793705540.asia-south2.run.app/
```

## 12. App Engine vs Cloud Run vs GKE

| Capability | App Engine Standard | Cloud Run | GKE |
| --- | --- | --- | --- |
| Infrastructure management | Minimal | Minimal | More operational work |
| Custom Docker image | No | Yes | Yes |
| Kubernetes control | No | No | Yes |
| Autoscaling | Yes | Yes | Configurable |
| Best fit | Managed Python web API | Containerized FastAPI and AI agents | Complex multi-service platform |
