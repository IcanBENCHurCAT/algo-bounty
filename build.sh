#!/usr/bin/env bash
set -e

# Target directories
ARTIFACTS_DIR="artifacts"
TEMP_BUILD_DIR="temp_build"

echo "=== Cleaning build directories ==="
rm -rf "$ARTIFACTS_DIR" "$TEMP_BUILD_DIR"
mkdir -p "$ARTIFACTS_DIR" "$TEMP_BUILD_DIR"

# Check if algokit is installed
if ! command -v algokit &> /dev/null; then
    if [ -f "venv/bin/algokit" ]; then
        ALGOKIT="venv/bin/algokit"
    elif [ -f "venv/Scripts/algokit" ]; then
        ALGOKIT="venv/Scripts/algokit"
    else
        echo "algokit command not found. Please ensure it is installed and in your PATH."
        exit 1
    fi
else
    ALGOKIT="algokit"
fi

echo "=== Compiling Testnet Variant ==="
# Testnet: DISPUTE_TIMEOUT=300 (5m), CLAIM_TIMEOUT=120 (2m)
$ALGOKIT compile python escrow.py \
  --out-dir "$TEMP_BUILD_DIR/testnet" \
  --output-teal \
  --template-var DISPUTE_TIMEOUT=300 \
  --template-var CLAIM_TIMEOUT=120

cp "$TEMP_BUILD_DIR/testnet/EscrowContract.approval.teal" "$ARTIFACTS_DIR/escrow_testnet.teal"
cp "$TEMP_BUILD_DIR/testnet/EscrowContract.clear.teal" "$ARTIFACTS_DIR/escrow_testnet_clear.teal"
cp "$TEMP_BUILD_DIR/testnet/EscrowContract.arc56.json" "$ARTIFACTS_DIR/escrow_testnet.arc56.json"

echo "=== Compiling Mainnet Variant ==="
# Mainnet: DISPUTE_TIMEOUT=2592000 (30d), CLAIM_TIMEOUT=172800 (48h)
$ALGOKIT compile python escrow.py \
  --out-dir "$TEMP_BUILD_DIR/mainnet" \
  --output-teal \
  --template-var DISPUTE_TIMEOUT=2592000 \
  --template-var CLAIM_TIMEOUT=172800

cp "$TEMP_BUILD_DIR/mainnet/EscrowContract.approval.teal" "$ARTIFACTS_DIR/escrow_mainnet.teal"
cp "$TEMP_BUILD_DIR/mainnet/EscrowContract.clear.teal" "$ARTIFACTS_DIR/escrow_mainnet_clear.teal"
cp "$TEMP_BUILD_DIR/mainnet/EscrowContract.arc56.json" "$ARTIFACTS_DIR/escrow_mainnet.arc56.json"

echo "=== Cleaning up temporary build directory ==="
rm -rf "$TEMP_BUILD_DIR"

echo "=== Build Completed Successfully! Artifacts saved in /$ARTIFACTS_DIR ==="
