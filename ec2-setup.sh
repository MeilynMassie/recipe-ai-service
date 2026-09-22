#!/bin/bash
set -euo pipefail

# Recommended instance: t3.large (2 vCPU / 8 GiB RAM), no GPU needed.
# gemma3:4b is ~3.3GB on disk/in memory, so anything under 8 GiB RAM
# (e.g. t3.medium) runs too close to the edge alongside the OS + app.

# Installs
sudo apt update
sudo apt install -y python3.12 python3.12-venv

# Ollama - the installer sets up its own systemd service (ollama.service),
# enabled and started automatically, bound to localhost:11434 by default.
curl -fsSL https://ollama.com/install.sh | sh
ollama pull gemma3:4b

git clone https://github.com/MeilynMassie/recipe-ai-service.git

# .venv
cd recipe-ai-service
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

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
