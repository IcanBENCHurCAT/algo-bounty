#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# AlgoBounty Gateway — GCP Cloud Run Deployment
#
# Deploys the AlgoBounty FastAPI gateway to Cloud Run.
# Uses Supabase for database (not Cloud SQL).
# All sensitive values are pulled from Secret Manager.
#
# Usage: ./deploy.sh
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ID="soul-seeker-500816"
REGION="us-central1"
SERVICE_NAME="algo-bounty-gateway"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:production"

GCLOUD_PATH="/home/st9797/google-cloud-sdk/bin/gcloud"

echo "🚀 AlgoBounty Gateway Deployment"
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo "   Image:   ${IMAGE_TAG}"
echo ""

# ── 1. Resolve secrets from Secret Manager ──────────────────────
echo "🔐 Resolving secrets from Secret Manager…"

SECRET_KEY="$(${GCLOUD_PATH} secrets versions access latest \
  --secret=algobounty_secret_key --project="${PROJECT_ID}" 2>/dev/null)" || SECRET_KEY=""

PLATFORM_PRIVATE_KEY="$(${GCLOUD_PATH} secrets versions access latest \
  --secret=algobounty_platform_private_key --project="${PROJECT_ID}" 2>/dev/null)" || PLATFORM_PRIVATE_KEY=""

GITHUB_WEBHOOK_SECRET="$(${GCLOUD_PATH} secrets versions access latest \
  --secret=algobounty_github_webhook_secret --project="${PROJECT_ID}" 2>/dev/null)" || GITHUB_WEBHOOK_SECRET=""

SUPABASE_SERVICE_ROLE_KEY="$(${GCLOUD_PATH} secrets versions access latest \
  --secret=algobounty_supabase_service_role_key --project="${PROJECT_ID}" 2>/dev/null)" || SUPABASE_SERVICE_ROLE_KEY=""

DATABASE_URL="$(${GCLOUD_PATH} secrets versions access latest \
  --secret=algobounty-db-url --project="${PROJECT_ID}" 2>/dev/null)" || DATABASE_URL=""

if [ -z "${SECRET_KEY}" ]; then
  echo "⚠️  SECRET_KEY not found in Secret Manager — setting placeholder"
fi

# ── 2. Build and push Docker image ───────────────────────────────
echo ""
echo "📦 Building and pushing image…"

${GCLOUD_PATH} builds submit --project="${PROJECT_ID}" --tag "${IMAGE_TAG}" . \
  --timeout=600

# ── 3. Deploy to Cloud Run ──────────────────────────────────────
echo ""
echo "🚀 Deploying to Cloud Run…"

SUPABASE_URL="${SUPABASE_URL:-https://mtivcwposaunlsiefwre.supabase.co}"
NEXT_PUBLIC_SUPABASE_URL="${NEXT_PUBLIC_SUPABASE_URL:-${SUPABASE_URL}}"
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY="${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY:-}"

${GCLOUD_PATH} run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_TAG}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --concurrency=10 \
  --max-instances=10 \
  --timeout=300 \
  --automatic-scaling-min-instances=0 \
  --set-env-vars="ALGORAND_NETWORK=testnet" \
  --set-env-vars="SUPABASE_URL=${SUPABASE_URL}" \
  --set-env-vars="NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}" \
  --set-env-vars="NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY}" \
  --set-env-vars="GITHUB_APP_ID=4213538" \
  --set-env-vars="GITHUB_CLIENT_ID=Iv23liTViZTezzWtUaul" \
  --set-secrets="SECRET_KEY=algobounty_secret_key" \
  --set-secrets="PLATFORM_PRIVATE_KEY=algobounty_platform_private_key" \
  --set-secrets="GITHUB_WEBHOOK_SECRET=algobounty_github_webhook_secret" \
  --set-secrets="SUPABASE_SERVICE_ROLE_KEY=algobounty_supabase_service_role_key" \
  --set-secrets="GITHUB_PRIVATE_KEY=algobounty-github-private-key:latest"
  --set-secrets="DATABASE_URL=algobounty-db-url:latest"

echo ""
echo "✅ AlgoBounty Gateway Deployment Complete!"

# Print the service URL
GATEWAY_URL=$(${GCLOUD_PATH} run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)' 2>/dev/null) || GATEWAY_URL="https://algo-bounty-gateway-soul-seeker-500816-uc.a.run.app"

echo "   Gateway URL: ${GATEWAY_URL}"
echo "   Health check: ${GATEWAY_URL}/health"
