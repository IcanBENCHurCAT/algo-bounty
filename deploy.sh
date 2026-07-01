#!/usr/bin/env bash
# AlgoBounty Gateway & Dashboard - GCP Cloud Run Deployment Script
#
# Usage: ./deploy.sh
#

set -euo pipefail

PROJECT_ID="soul-seeker-500816"
REGION="us-central1"
SERVICE_NAME="algo-bounty-gateway"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:production"

# Use absolute path to gcloud on the server
GCLOUD_PATH="/home/st9797/google-cloud-sdk/bin/gcloud"

echo "🚀 Starting AlgoBounty deployment to Google Cloud Run..."
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo ""

# 1. Build and push Docker image using Google Cloud Build
echo "📦 Submitting build to Google Cloud Build..."
$GCLOUD_PATH builds submit --project="${PROJECT_ID}" --tag "${IMAGE_TAG}" .

# 2. Deploy the container to Google Cloud Run
echo "🚀 Deploying service to Google Cloud Run..."
$GCLOUD_PATH run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_TAG}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --set-secrets="SECRET_KEY=algobounty-jwt-secret:latest,GITHUB_WEBHOOK_SECRET=algobounty-github-webhook-secret:latest" \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  --concurrency=80

echo ""
echo "✅ AlgoBounty Deployment Complete!"
echo "   URL: https://algo-bounty-gateway-soul-seeker-500816-uc.a.run.app"
