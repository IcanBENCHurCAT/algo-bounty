#!/usr/bin/env python3
import os
import re
import sys
import subprocess

base_dir = os.path.dirname(os.path.abspath(__file__))
contract_path = os.path.join(base_dir, 'escrow.algo')
teal_path = os.path.join(base_dir, 'escrow.teal')

print('=== Compiling escrow.algo -> escrow.teal ===')

# Try algokit first
try:
    result = subprocess.run(
        ['algokit', 'compile', contract_path, '-o', teal_path],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0 and os.path.exists(teal_path):
        print(f'algokit succeeded: {os.path.getsize(teal_path)} bytes')
        sys.exit(0)
except FileNotFoundError:
    print('algokit not found')

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
