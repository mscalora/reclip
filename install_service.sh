#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo)"
  exit 1
fi

APP_DIR="/opt/reclip"

echo "Creating 'reclip' system user..."
if ! id -u reclip > /dev/null 2>&1; then
    useradd -r -s /bin/false -d $APP_DIR reclip
fi

echo "Installing system dependencies..."
apt-get update
apt-get install -y python3-venv ffmpeg

echo "Setting up application directory at $APP_DIR..."
mkdir -p $APP_DIR
cp -r . $APP_DIR/
rm -rf $APP_DIR/venv $APP_DIR/__pycache__
chown -R reclip:reclip $APP_DIR

echo "Setting up Python virtual environment..."
sudo -u reclip bash -c "cd $APP_DIR && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"

echo "Creating systemd service..."
cat > /etc/systemd/system/reclip.service << 'EOF'
[Unit]
Description=ReClip Video Downloader
After=network.target

[Service]
User=reclip
Group=reclip
WorkingDirectory=/opt/reclip
Environment="PATH=/opt/reclip/venv/bin"
Environment="FLASK_APP=app.py"
ExecStart=/opt/reclip/venv/bin/flask run --host=127.0.0.1 --port=8899
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable reclip
systemctl restart reclip

echo "====================================="
echo "ReClip service installed successfully!"
echo "It is now running under the 'reclip' user."
echo "Check status: sudo systemctl status reclip"
echo "View logs: sudo journalctl -u reclip -f"
echo "====================================="
