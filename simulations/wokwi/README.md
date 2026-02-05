# Wokwi Simulation: Infant Security System

This project contains the simulation artifacts for the Infant Security System. The system simulates an Infant Tag (IT), Mother Tag (MT), Gate Reader (GR), and Gate Terminal (GT).

## Prerequisites

- [Wokwi for VS Code](https://marketplace.visualstudio.com/items?itemName=wokwi.wokwi-vscode) OR access to [Wokwi.com](https://wokwi.com).
- Python 3 installed (for the setup script).

## Project Structure

- `common/`: Shared code (Config, MQTT, Security).
- `infant_tag/`: Firmware and Project for Infant Tag.
- `mother_tag/`: Firmware and Project for Mother Tag.
- `gate_reader/`: Firmware and Project for Gate Reader.
- `gate_terminal/`: Firmware and Project for Gate Terminal.

## Setup

1.  **Install mpremote**:
    ```bash
    pip install mpremote
    ```
    *(The deployment script handles this too, but good to have)*.

2.  **Configuration**:
    - `wokwi.toml` files are configured with unique ports:
        - Infant Tag: 4001
        - Mother Tag: 4002
        - Gate Reader: 4003
        - Gate Terminal: 4004

3.  **MicroPython Firmware (VS Code Only)**:
    - Ensure `micropython.bin` is in each folder (already done).

## Running the Simulation

1.  **Start Simulator**:
    - Open each project folder and Start Simulator (Right-click `diagram.json`).
    - **IMPORTANT**: Start them ALL or at least the ones you want to update.
    - Keep them running.

2.  **Deploy Code**:
    - Run the deployment script to upload `main.py` and libraries to the running simulators:
    ```bash
    cd simulations/wokwi
    chmod +x deploy.sh
    ./deploy.sh
    ```
    - Check the terminal output to confirm files are uploaded.
    - The script will reset the devices automatically.
2.  **Recommended Order**:
    - Start **Gate Terminal** (to see logs).
    - Start **Gate Reader** (to handle gate events).
    - Start **Infant Tag** (starts broadcasting presence).
    - Start **Mother Tag** (starts broadcasting presence).

## Test Scenarios

### 1. Happy Path: Authorized Exit
1.  **Ensure IT and MT are Paired**:
    - On **Mother Tag**: Press the **BLUE** button (Pair).
    - Check **Infant Tag** logs: `Saved pairing`.
    - Check **Mother Tag** logs: `Pairing SUCCESS`.
2.  **Simulate Gate Entry**:
    - On **Gate Reader**: Press the **GREEN** button (Scan IT-0001).
    - **Gate Reader** should log broadcast `Authorized!`.
    - **Green LED** on GR should light up.
    - **Gate Terminal** should log `GATE EVENT` with `authorized: true`.

### 2. Unauthorized Exit (No Pairing Presence)
1.  **Disable Mother Tag** (Stop simulation or wait > 30s so presence expires).
2.  **Simulate Gate Entry**:
    - On **Gate Reader**: Press the **GREEN** button.
    - **Gate Reader** should log `Mother not seen` or similar.
    - **Red LED** on GR should light up.
    - **Gate Reader** sends Alarm.
    - **Gate Terminal** logs `ALARM RECEIVED`.

### 3. Panic Button
1.  On **Infant Tag**: Press the **RED** button.
2.  **Infant Tag** sends `alarm` message.
3.  **Gate Terminal** receives ALARM.

### 4. Cancel Alarm
1.  On **Mother Tag**: Press the **GREEN** button (Cancel).
2.  **Mother Tag** sends `cancel_alarm` command.
3.  **Gate Terminal** logs `Command Audit: cancel_alarm`.

## Pairing Workflow

1.  **Mother Tag** initiates: Publishes `security/pairing/<TARGET_IT>` with payload `{type: "pair_request", mother_id: <MY_ID>}`.
2.  **Infant Tag** receives: Verifies signature. Saves `mother_id`.
3.  **Infant Tag** responds: Publishes `security/pairing/<MOTHER_ID>` with payload `{type: "pair_ack", infant_id: <MY_ID>}`.
4.  **Mother Tag** receives: Verifies signature. Saves `infant_id`. Pairing Complete.

## Security Notes

- **HMAC Signatures**: All messages are signed with HMAC-SHA256 using the key in `config.py` (`SECRET_KEY`).
- **Replay Protection**: Messages include a timestamp (`ts`) and are rejected if >120s old.
- **Production**: In a real deployment, use individual device keys (Pre-Shared Keys) or certificates, and rotate nonces strictly.

## Troubleshooting

- **MQTT Connect Failed**: Check your internet connection. `WOKWI-GUEST` acts as a gateway. Try changing broker in `config.py`.
- **Import Error (no module common)**: Run `./setup_projects.sh` again.
- **Bad Signature**: Ensure all devices have the same `SECRET_KEY` in `config.py` (or `simulation_specs.json`).
