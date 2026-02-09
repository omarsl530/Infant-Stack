#!/bin/bash
set -e

# Helper to run mpremote
MPREMOTE="python3 -m mpremote"
PORT="port:rfc2217://localhost:4005"

echo "Deploying to SSD1306 Example (Port 4005)..."

# Upload files
echo "   Uploading files..."
$MPREMOTE connect $PORT fs cp esp32-micropython-ssd1306/main.py :main.py
$MPREMOTE connect $PORT fs cp esp32-micropython-ssd1306/ssd1306.py :ssd1306.py

echo "   Verifying filesystem..."
$MPREMOTE connect $PORT fs ls

echo "   Resetting and Running main..."
$MPREMOTE connect $PORT soft-reset
# Explicitly import main to ensure it runs even if auto-boot fails
$MPREMOTE connect $PORT exec "import main"

echo "Deployment Complete!"
