#!/bin/bash
set -e

# Helper to run mpremote
MPREMOTE="python3 -m mpremote"

echo "Deploying to Infant Tag (Port 4001)..."
# Upload common modules
echo "   Uploading common modules..."
$MPREMOTE connect port:rfc2217://localhost:4001 fs mkdir common || true
for f in common/*.py; do
    $MPREMOTE connect port:rfc2217://localhost:4001 fs cp $f :$f
done
# Upload device files
echo "   Uploading device files..."
$MPREMOTE connect port:rfc2217://localhost:4001 fs cp infant_tag/main.py :main.py
$MPREMOTE connect port:rfc2217://localhost:4001 fs cp infant_tag/boot.py :boot.py
$MPREMOTE connect port:rfc2217://localhost:4001 fs cp simulation_specs.json :simulation_specs.json || true
# Reset and Run
$MPREMOTE connect port:rfc2217://localhost:4001 soft-reset
$MPREMOTE connect port:rfc2217://localhost:4001 exec "import main"

echo "Deploying to Mother Tag (Port 4002)..."
$MPREMOTE connect port:rfc2217://localhost:4002 fs mkdir common || true
for f in common/*.py; do
    $MPREMOTE connect port:rfc2217://localhost:4002 fs cp $f :$f
done
$MPREMOTE connect port:rfc2217://localhost:4002 fs cp mother_tag/main.py :main.py
$MPREMOTE connect port:rfc2217://localhost:4002 fs cp simulation_specs.json :simulation_specs.json || true
# Reset and Run
$MPREMOTE connect port:rfc2217://localhost:4002 soft-reset
$MPREMOTE connect port:rfc2217://localhost:4002 exec "import main"

echo "Deploying to Gate Reader (Port 4003)..."
$MPREMOTE connect port:rfc2217://localhost:4003 fs mkdir common || true
for f in common/*.py; do
    $MPREMOTE connect port:rfc2217://localhost:4003 fs cp $f :$f
done
$MPREMOTE connect port:rfc2217://localhost:4003 fs cp gate_reader/main.py :main.py
$MPREMOTE connect port:rfc2217://localhost:4003 fs cp simulation_specs.json :simulation_specs.json || true
# Reset and Run
$MPREMOTE connect port:rfc2217://localhost:4003 soft-reset
$MPREMOTE connect port:rfc2217://localhost:4003 exec "import main"

echo "Deploying to Gate Terminal (Port 4004)..."
$MPREMOTE connect port:rfc2217://localhost:4004 fs mkdir common || true
for f in common/*.py; do
    $MPREMOTE connect port:rfc2217://localhost:4004 fs cp $f :$f
done
$MPREMOTE connect port:rfc2217://localhost:4004 fs cp gate_terminal/main.py :main.py
$MPREMOTE connect port:rfc2217://localhost:4004 fs cp simulation_specs.json :simulation_specs.json || true
# Reset and Run
$MPREMOTE connect port:rfc2217://localhost:4004 soft-reset
$MPREMOTE connect port:rfc2217://localhost:4004 exec "import main"