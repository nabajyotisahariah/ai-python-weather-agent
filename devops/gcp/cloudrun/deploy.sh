```bash
#!/usr/bin/env bash

set -euo pipefail

# ============================================================
# AI Weather Agent - GCP Cloud Run Deployment
#
# Usage:
#   ./deploy.sh staging
#   ./deploy.sh production
#
# Prerequisites:
#   - gcloud
#   - docker
#   - authenticated gcloud account
#   - configured GCP project
# ============================================================

ENVIRONMENT="${1:-}"

if [[ -z "$ENVIRONMENT" ]]; then
    echo "Usage: ./deploy.sh [staging|production]"
    exit 1
fi

if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo "ERROR: Environment must be staging or production"
    exit 1
fi


# ============================================================
# Environment Configuration
#Artifact Repo Path
# asia-south2-docker.pkg.dev/project-workspace-511112/artifact-ai-python-weather-agent
# ============================================================

if [[ "$ENVIRONMENT" == "staging" ]]; then

    PROJECT_ID=project-workspace-stg
    REGION=asia-south2

    SERVICE=app2-ai-python-weather
    SERVICE_ACCOUNT=service2-ai-python-weather
    REPOSITORY=artifact2-ai-python-weather-agent
    IMAGE=ai2-python-weather-agent
    TAG=1.0

    MIN_INSTANCES=0
    MAX_INSTANCES=1

    MEMORY="1Gi"
    CPU="1"

    ENV_VARS="ENVIRONMENT=staging,LOG_LEVEL=DEBUG"

elif [[ "$ENVIRONMENT" == "production" ]]; then

    PROJECT_ID=project-workspace-511112
    REGION=asia-south2
    
    SERVICE=app2-ai-python-weather
    SERVICE_ACCOUNT=service2-ai-python-weather
    REPOSITORY=artifact2-ai-python-weather-agent
    IMAGE=ai2-python-weather-agent
    TAG=1.0

    MIN_INSTANCES=0
    MAX_INSTANCES=1

    MEMORY="1Gi"
    CPU="1"

    ENV_VARS="ENVIRONMENT=production,LOG_LEVEL=INFO"

fi


# ============================================================
# Configuration
# ============================================================

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE}:${TAG}"


echo ""
echo "============================================================"
echo " AI Weather Agent Deployment"
echo "============================================================"
echo " Environment      : ${ENVIRONMENT}"
echo " Project          : ${PROJECT_ID}"
echo " Region           : ${REGION}"
echo " Service Account  : ${SERVICE_ACCOUNT}"
echo " Image            : ${IMAGE_URI}"
echo " Min Instances    : ${MIN_INSTANCES}"
echo " Max Instances    : ${MAX_INSTANCES}"
echo "============================================================"
echo ""


# ============================================================
# Step 1 - Set GCP Project
# ============================================================

echo ">>> Setting GCP project..."

gcloud config set project "${PROJECT_ID}"


# ============================================================
# Step 2 - Enable Required APIs
# ============================================================

echo ">>> Enabling required GCP APIs..."

gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    --project="${PROJECT_ID}"


# ============================================================
# Step 3 - Create Artifact Registry Repository
# ============================================================

echo ">>> Checking Artifact Registry repository..."

if ! gcloud artifacts repositories describe "${REPOSITORY}" \
    --location="${REGION}" >/dev/null 2>&1; then

    echo ">>> Creating Artifact Registry repository..."

    gcloud artifacts repositories create "${REPOSITORY}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="AI Weather Agent Docker Repository"

else

    echo ">>> Artifact Registry repository already exists."

fi


# ============================================================
# Step 4 - Configure Docker Authentication
# ============================================================

echo ">>> Configuring Docker authentication..."

gcloud auth configure-docker \
    "${REGION}-docker.pkg.dev" \
    --quiet


# ============================================================
# Step 5 - Build Docker Image
# ============================================================

echo ">>> Building Docker image..."

docker build \
    -t "${IMAGE_URI}" .


# ============================================================
# Step 6 - Push Docker Image
# ============================================================

echo ">>> Pushing Docker image..."

docker push "${IMAGE_URI}"


# ============================================================
# Step 7 - Deploy to Cloud Run
# ============================================================

echo ">>> Deploying Cloud Run service..."

gcloud run deploy "${SERVICE}" \
    --project="${PROJECT_ID}" \
    --image="${IMAGE_URI}" \
    --region="${REGION}" \
    --service-account="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --port=8000 \
    --memory="${MEMORY}" \
    --cpu="${CPU}" \
    --min="${MIN_INSTANCES}" \
    --max-instances="${MAX_INSTANCES}" \
    --set-env-vars="${ENV_VARS}" \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,GOOGLE_API_KEY=GOOGLE_API_KEY:latest,REDIS_URL=REDIS_URL:latest,LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest,LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest" \
    --allow-unauthenticated


# ============================================================
# Step 8 - Get Service URL
# ============================================================

SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
    --region="${REGION}" \
    --format="value(status.url)")


# ============================================================
# Deployment Completed
# ============================================================

echo ""
echo "============================================================"
echo " Deployment Successful"
echo "============================================================"
echo " Environment : ${ENVIRONMENT}"
echo " Service     : ${SERVICE}"
echo " Image       : ${IMAGE_URI}"
echo " URL         : ${SERVICE_URL}"
echo "============================================================"
echo ""
```
