#!/bin/bash
set -e

# Wokwi CLI Path
WOKWI_CLI="/home/omarsl530/bin/wokwi-cli"

# Load .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

if [ -z "$WOKWI_CLI_TOKEN" ]; then
    echo "Error: WOKWI_CLI_TOKEN is not set."
    echo "Please get a free token from https://wokwi.com/dashboard/ci"
    echo "Then run: export WOKWI_CLI_TOKEN=your_token_here"
    exit 1
fi

echo "Starting Simulations in Background (1 hour timeout)..."

# Cleanup old pids
if [ -f .wokwi_pids ]; then
    echo "Cleaning up old processes..."
    kill $(cat .wokwi_pids) 2>/dev/null || true
    rm .wokwi_pids
fi

# Function to start a sim
start_sim() {
    DIR=$1
    echo "Starting $DIR..."
    # Run with 1 hour timeout (3600000 ms)
    $WOKWI_CLI $DIR --timeout 3600000 > /dev/null 2>&1 &
    PID=$!
    echo "$DIR started (PID $PID)"
    echo $PID >> .wokwi_pids
}

start_sim "simulations/wokwi/infant_tag"
start_sim "simulations/wokwi/mother_tag"
start_sim "simulations/wokwi/gate_reader"
start_sim "simulations/wokwi/gate_terminal"
start_sim "simulations/wokwi/esp32-micropython-ssd1306"

echo "All simulations started! You have 1 hour."
echo "Wait 5 seconds for them to boot..."
sleep 5
echo "You can now run ./deploy.sh"
echo "To stop them manually, run: kill \$(cat .wokwi_pids) && rm .wokwi_pids"
