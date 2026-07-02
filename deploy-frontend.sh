#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# AlgoBounty Dashboard (Frontend) — GCP Cloud Run Deployment
#
# Builds Next.js dashboard and deploys to Cloud Run.
#
# Usage: ./deploy-frontend.sh
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

PROJECT_ID="soul-seeker-500816"
REGION="us-central1"
SERVICE_NAME="algo-bounty-frontend"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:production"

GCLOUD_PATH="/home/st9797/google-cloud-sdk/bin/gcloud"

echo "🚀 AlgoBounty Frontend Deployment"
echo "   Project: ${PROJECT_ID}"
echo "   Region:  ${REGION}"
echo "   Service: ${SERVICE_NAME}"
echo "   Image:   ${IMAGE_TAG}"
echo ""

# ── 1. Resolve secrets from Secret Manager ──────────────────────
echo "🔐 Resolving secrets from Secret Manager…"

SUPABASE_URL="${SUPABASE_URL:-https://mtivcwposaunlsiefwre.supabase.co}"
NEXT_PUBLIC_SUPABASE_URL="${NEXT_PUBLIC_SUPABASE_URL:-${SUPABASE_URL}}"

NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY="$(${GCLOUD_PATH} secrets versions access latest \
  --secret=algobounty_supabase_publishable_key --project="${PROJECT_ID}" 2>/dev/null)" || NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=""

# Gateway URL for API calls
GATEWAY_URL="$(${GCLOUD_PATH} run services describe "algo-bounty-gateway" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)' 2>/dev/null)" || GATEWAY_URL="https://algo-bounty-gateway-soul-seeker-500816-uc.a.run.app"

echo "   Supabase URL:  ${NEXT_PUBLIC_SUPABASE_URL}"
echo "   Gateway URL:   ${GATEWAY_URL}"
echo ""

# ── 2. Build and push Docker image ───────────────────────────────
echo "📦 Building and pushing image…"

# Build from the dashboard directory context (Dockerfile lives there)
${GCLOUD_PATH} builds submit --project="${PROJECT_ID}" --tag "${IMAGE_TAG}" dashboard/

# ── 3. Deploy to Cloud Run ──────────────────────────────────────
echo "🚀 Deploying to Cloud Run…"

${GCLOUD_PATH} run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_TAG}" \
  --platform=managed \
  --allow-unauthenticated \
  --port=8080 \
  --memory=256Mi \
  --cpu=1 \
  --concurrency=250 \
  --timeout=60 \
  --min-instances=0 \ 
  --set-env-vars="NEXT_PUBLIC_SUPABASE_URL=${NEXT_PUBLIC_SUPABASE_URL}" \
  --set-env-vars="NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=${NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY}" \
  --set-env-vars="NEXT_PUBLIC_API_URL=${GATEWAY_URL}" \
  2>&1

echo ""
echo "✅ AlgoBounty Frontend Deployment Complete!"

FRONTEND_URL="$(${GCLOUD_PATH} run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)' 2>/dev/null)" || FRONTEND_URL="https://algo-bounty-frontend-soul-seeker-500816-uc.a.run.app"

echo "   Frontend URL: ${FRONTEND_URL}"
