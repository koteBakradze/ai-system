#!/bin/bash
set -euo pipefail

cd "$(dirname "$0")/.."
python scripts/scan_environment.py
