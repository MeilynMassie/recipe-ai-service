#!/bin/bash
set -euo pipefail

# Recommended instance: t3.large (2 vCPU / 8 GiB RAM), no GPU needed.
# gemma3:4b is ~3.3GB on disk/in memory, so anything under 8 GiB RAM
# (e.g. t3.medium) runs too close to the edge alongside the OS + app.

# Python version: override with `PYTHON_VERSION=3.14 ./ec2-setup.sh` or `./ec2-setup.sh 3.14`
PYTHON_VERSION="${1:-${PYTHON_VERSION:-3.12}}"
PYTHON_BIN="python${PYTHON_VERSION}"

# Installs
sudo apt update
sudo apt install -y "$PYTHON_BIN" "${PYTHON_BIN}-venv"
echo "Downloaded python${PYTHON_VERSION} "

# Ollama - the installer sets up its own systemd service (ollama.service),
# enabled and started automatically, bound to localhost:11434 by default.
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:4b
echo "Downloaded Ollama"

# git clone https://github.com/MeilynMassie/recipe-ai-service.git

# .venv
"$PYTHON_BIN" -m venv .venv
source .venv/bin/activate
echo "Created .venv"
pip install -r requirements.txt
echo "Downloaded libraries"

# Run the API as a systemd service so it restarts on crash/reboot instead of
# needing a manually-kept-alive terminal session.
APP_DIR="$(pwd)"
sudo tee /etc/systemd/system/recipe-ai-service.service > /dev/null <<EOF
[Unit]
Description=Recipe AI Service (FastAPI)
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now recipe-ai-service

echo "Recipe AI Service running as a systemd service on port 9000."
echo "Check status with: sudo systemctl status recipe-ai-service"
echo "Tail logs with:    sudo journalctl -u recipe-ai-service -f"
