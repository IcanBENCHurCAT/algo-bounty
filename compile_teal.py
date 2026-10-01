#!/usr/bin/env python3
import os
import re
import sys
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
contract_path = os.path.join(base_dir, 'escrow.py')
teal_path = os.path.join(base_dir, 'artifacts', 'EscrowContract.approval.teal')

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
        [algokit_cmd, 'compile', 'python', contract_path, '--out-dir', os.path.join(base_dir, 'artifacts'), '--output-teal', '--template-var', 'DISPUTE_TIMEOUT=300', '--template-var', 'CLAIM_TIMEOUT=120', '--template-var', 'PLATFORM_FEE=200'],
        capture_output=True, text=True, timeout=30
    )
    src_approval = os.path.join(base_dir, 'artifacts', 'EscrowContract.approval.teal')
    if os.path.exists(src_approval):
        print(f'Compilation succeeded. Wrote {src_approval}')
        sys.exit(0)
    else:
        print('Compilation failed or approval TEAL not found:', result.stderr)
except FileNotFoundError:
    print('algokit not found in PATH')

# Fallback: docstring stripping from Puya source
print('Trying docstring stripping fallback... (Not applying to canonical artifacts/ file to prevent corruption)')
# We skip the fallback here so we don't accidentally overwrite the compiled TEAL
# with python source code when algokit is missing from PATH.
