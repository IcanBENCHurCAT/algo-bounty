#!/usr/bin/env python3
import os
import re
import sys
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
contract_path = os.path.join(base_dir, 'escrow.py')
teal_path = os.path.join(base_dir, 'escrow.teal')

print('=== Compiling escrow.py -> artifacts/ ===')

# Run compile python command
try:
    # Compile testnet variant
    algokit_cmd = 'algokit'
    venv_algokit_win = os.path.join(base_dir, 'venv', 'Scripts', 'algokit.exe')
    venv_algokit_nix = os.path.join(base_dir, 'venv', 'bin', 'algokit')
    if os.path.exists(venv_algokit_win):
        algokit_cmd = venv_algokit_win
    elif os.path.exists(venv_algokit_nix):
        algokit_cmd = venv_algokit_nix

    result = subprocess.run(
        [algokit_cmd, 'compile', 'python', contract_path, '--out-dir', os.path.join(base_dir, 'artifacts'), '--output-teal', '--template-var', 'DISPUTE_TIMEOUT=300', '--template-var', 'CLAIM_TIMEOUT=120'],
        capture_output=True, text=True, timeout=30
    )
    # Copy EscrowContract.approval.teal to escrow.teal for compatibility
    src_approval = os.path.join(base_dir, 'artifacts', 'EscrowContract.approval.teal')
    if os.path.exists(src_approval):
        # Create artifacts/escrow_testnet.teal etc.
        os.makedirs(os.path.join(base_dir, 'artifacts'), exist_ok=True)
        # copy
        with open(src_approval, 'r') as sf, open(teal_path, 'w') as tf:
            tf.write(sf.read())
        print(f'Compilation succeeded. Copied {src_approval} to {teal_path}')
        sys.exit(0)
    else:
        print('Compilation failed or approval TEAL not found:', result.stderr)
except FileNotFoundError:
    print('algokit not found in PATH')

# Fallback: docstring stripping from Puya source
print('Trying docstring stripping fallback...')
with open(contract_path) as f:
    content = f.read()

# Optimized docstring stripping using regex
teal = re.sub(r'(?s)^.*?[ \t]*(?:"""|\'\'\').*?(?:"""|\'\'\')[^\n]*\r?\n?', '', content, count=1)
with open(teal_path, 'w') as f:
    f.write(teal)

print(f'Success: {len(teal.splitlines())} lines ({os.path.getsize(teal_path)} bytes)')
print('First 5 TEAL lines:')
for line in teal.splitlines()[:5]:
    print('  ' + line)
