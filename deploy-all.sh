#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
# AlgoBounty — One-command Deploy (Gateway + Dashboard)
#
# Runs gateway deploy first, then waits briefly and deploys
# the dashboard frontend (which depends on knowing the gateway URL).
#
# Usage: ./deploy-all.sh
# ═══════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         AlgoBounty — Full Deployment Pipeline               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Deploy Gateway ──────────────────────────────────────
echo -e "${YELLOW}▶ Step 1/2: Deploying Gateway${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -x "${SCRIPT_DIR}/deploy.sh" ]; then
  bash "${SCRIPT_DIR}/deploy.sh"
else
  echo -e "${RED}✖ deploy.sh not found or not executable${NC}"
  exit 1
fi

echo ""

# Brief pause for Cloud Run to stabilise
echo "⏳ Waiting for gateway to stabilise…"
sleep 10

# ── Step 2: Deploy Dashboard ────────────────────────────────────
echo ""
echo -e "${YELLOW}▶ Step 2/2: Deploying Frontend Dashboard${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -x "${SCRIPT_DIR}/deploy-frontend.sh" ]; then
  bash "${SCRIPT_DIR}/deploy-frontend.sh"
else
  echo -e "${RED}✖ deploy-frontend.sh not found or not executable${NC}"
  exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                   Deployment Complete!                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
