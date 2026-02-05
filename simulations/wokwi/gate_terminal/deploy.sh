#!/bin/bash
set -e
MPREMOTE="python3 -m mpremote"
# Port 4004 defined in wokwi.toml
PORT="port:rfc2217://localhost:4004"

echo "Deploying Gate Terminal (Port 4004)..."

# Upload Common Modules
echo "  > Uploading common modules..."
$MPREMOTE connect $PORT fs mkdir common || true
for f in ../common/*.py; do
    FNAME=$(basename $f)
    $MPREMOTE connect $PORT fs cp $f :common/$FNAME
done

# Upload Device Files
echo "  > Uploading device files..."
$MPREMOTE connect $PORT fs cp main.py :main.py
if [ -f boot.py ]; then
    $MPREMOTE connect $PORT fs cp boot.py :boot.py
fi
if [ -f ../simulation_specs.json ]; then
    $MPREMOTE connect $PORT fs cp ../simulation_specs.json :simulation_specs.json
fi

# Reset and Force Run
echo "  > Resetting..."
$MPREMOTE connect $PORT soft-reset
$MPREMOTE connect $PORT exec "import main"

echo "Gate Terminal Deployed Successfully!"
