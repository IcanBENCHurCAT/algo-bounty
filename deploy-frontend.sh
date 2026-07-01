#!/usr/bin/env bash
# AlgoBounty Frontend (Next.js & Supabase) - GCP Cloud Run Deployment Script
#

set -euo pipefail

PROJECT_ID="soul-seeker-500816"
REGION="us-central1"
SERVICE_NAME="algo-bounty-frontend"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:production"

# Use absolute path to gcloud on the server
GCLOUD_PATH="/home/st9797/google-cloud-sdk/bin/gcloud"

echo "🚀 Starting AlgoBounty Frontend deployment to Google Cloud Run..."
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo ""

# 1. Build and push Next.js container image using Google Cloud Build
echo "📦 Submitting build to Google Cloud Build..."
$GCLOUD_PATH builds submit --project="${PROJECT_ID}" --tag "${IMAGE_TAG}" --async dashboard/

# 2. Deploy the container to Google Cloud Run
echo "🚀 Deploying service to Google Cloud Run..."
$GCLOUD_PATH run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_TAG}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --set-env-vars="NEXT_PUBLIC_SUPABASE_URL=https://mtivcwposaunlsiefwre.supabase.co,NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=sb_publishable_SOX8CHhnDWw3a7DsScmKuw_8HFPR2h0" \
  --memory=1Gi \
  --cpu=1 \
  --timeout=300 \
  --concurrency=80

echo ""
echo "✅ AlgoBounty Frontend Deployment Complete!"
echo "   URL: https://algo-bounty-frontend-soul-seeker-500816-uc.a.run.app"
