#!/usr/bin/env bash
set -e

echo "============================================="
echo " AlgoBounty Escrow Smart Contract Deployer"
echo "============================================="
echo ""
echo "PAUSED: Please configure your creator wallet credentials (PLATFORM_PRIVATE_KEY) in gateway/.env"
echo "before proceeding. If you want to use a custom account, set it now."
echo ""
read -p "Press [Enter] when you are ready to deploy to Testnet..."

# Load environment variables if .env exists
if [ -f gateway/.env ]; then
    echo "Loading environment variables from gateway/.env..."
    export $(grep -v '^#' gateway/.env | xargs)
fi

# Ensure ALGORAND_NETWORK is testnet
export ALGORAND_NETWORK=testnet

# Run the deployment python script
export PYTHONPATH=.
python gateway/deploy_escrow.py
