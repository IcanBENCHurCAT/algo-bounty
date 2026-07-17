---
name: "algo-compile"
description: "Compile Algorand Python (`algopy`) smart contracts into TEAL and ARC-56 / ABI artifacts using the project's compile_teal.py script."
compatibility: "Requires the repository compile_teal.py script and algokit installed."
metadata:
  author: "algobounty-project"
  source: "custom-skills"
---

## Description
This skill documents how to compile Algorand Python (`algopy`) smart contracts (e.g., `escrow.py`) correctly within this project. The project provides a `compile_teal.py` script in the root directory that orchestrates the `algokit compile python` command to produce the TEAL and ARC-56 application JSON artifacts.

## Usage Guidelines
Whenever you modify an `algopy` smart contract, you **must** recompile it to generate the updated TEAL, map, and ARC-56 files. Failing to do so will result in outdated contract artifacts being deployed.

### Steps
1. Run the compilation script from the root directory:
   ```bash
   python3 compile_teal.py
   ```
2. Verify that the command succeeds and creates/updates the relevant `.teal`, `.json`, and `.puya.map` files (for instance, `EscrowContract.approval.teal`, `EscrowContract.clear.teal`, `EscrowContract.arc56.json`, etc.).
3. Commit these updated artifacts alongside your contract `.py` modifications, as they are essential for the backend tests and deployments.

## Common Issues
- **Syntax or Compile Errors**: Check the output of `python3 compile_teal.py`. If it fails, ensure that you are adhering to Puya / `algopy` limitations (e.g., proper use of `arc4.Struct`, typing arrays with `typing.Literal`, etc.).
- **Missing python packages**: The script might rely on `algokit-utils` or `algorand-python`. Make sure the current Python environment (as defined by `requirements.txt` or `poetry`) is set up correctly, although `compile_teal.py` wraps `algokit compile python` which generally handles its own subprocess execution.
