#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found. Install Python 3.11+ in WSL first."
  exit 1
fi

VENV_DIR="${ROOT_DIR}/.venv-wsl"
if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
  echo "[INFO] Creating WSL virtual environment at .venv-wsl"
  if ! python3 -m venv "${VENV_DIR}"; then
    echo "[ERROR] Failed to create venv. Install python3-venv and retry."
    echo "        Example: sudo apt-get update && sudo apt-get install -y python3-venv"
    exit 1
  fi
fi

source "${VENV_DIR}/bin/activate"

if ! python -m pip --version >/dev/null 2>&1; then
  echo "[INFO] pip not found in venv. Bootstrapping with ensurepip..."
  if ! python -m ensurepip --upgrade; then
    echo "[ERROR] Failed to bootstrap pip in venv."
    exit 1
  fi
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pytest -q "$@"
