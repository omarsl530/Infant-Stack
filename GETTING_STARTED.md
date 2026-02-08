# Getting Started with Infant-Stack

This guide explains how to run the Infant-Stack hospital infant tracking system locally.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** (to clone the repository)
- **Node.js 20+** (if running dashboards locally without Docker)
- **Python 3.11+** (for running simulations)
- Ports **3000-3003**, **8000**, **8080**, **5432**, **27017**, **6379**, **1883**, **9001** available

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/omarsl530/Infant-Stack.git
cd Infant-Stack
```

### 2. Configure Environment

Copy the example environment file:

**Linux/macOS:**
```bash
cp .env.example .env
```

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

### 3. Start All Services

```bash
docker-compose up -d
```

> **Note:** On first run, the dashboard containers will install npm dependencies (takes 2-3 minutes). Wait for this to complete before accessing the dashboards.

This starts:

- **Keycloak** (port 8080) - Identity and Access Management
- **PostgreSQL** (port 5432) - Primary database
- **MongoDB** (port 27017) - Time-series logs
- **Redis** (port 6379) - Cache/sessions
- **MQTT Broker** (ports 1883, 9001) - Real-time tag communication
- **API Gateway** (port 8000) - REST API
- **Device Gateway** - MQTT-to-database bridge
- **Dashboards**:
  - **Home Dashboard**: [http://localhost:3003](http://localhost:3003)
  - **Nurse Dashboard**: [http://localhost:3000](http://localhost:3000)
  - **Security Dashboard**: [http://localhost:3001](http://localhost:3001)
  - **Admin Dashboard**: [http://localhost:3002](http://localhost:3002)

### 4. Access the Identity Provider

Manage users and roles via Keycloak: [http://localhost:8080](http://localhost:8080)

- **Default Username**: `admin`
- **Default Password**: `admin123`

## Verification

Check all services are running:

```bash
docker-compose ps
```

Test the API:

**Linux/macOS:**
```bash
curl http://localhost:8000/health
```

**Windows (PowerShell):**
```powershell
Invoke-RestMethod http://localhost:8000/health
```

---

## Running Simulations

The project includes two simulation options for testing the system.

### Option 1: Python API Simulation

Simulates IoT devices (infant tags, RTLS readers, gate terminals, alarm nodes) that communicate with the backend APIs.

**Windows (PowerShell):**
```powershell
# Basic run
.\run_python_simulation.ps1

# Fast mode (for quick testing)
.\run_python_simulation.ps1 -FastMode

# With custom parameters
.\run_python_simulation.ps1 -NumInfants 10 -NumReaders 5 -Debug
```

**Linux/macOS:**
```bash
python simulation/main.py

# Fast mode
FAST_MODE=1 python simulation/main.py
```

### Option 2: Wokwi Hardware Simulations

Simulates ESP32/MicroPython hardware devices using Wokwi.

**Prerequisites:**
1. Get a free Wokwi CLI token from https://wokwi.com/dashboard/ci
2. Set the token in your environment

**Windows (PowerShell):**
```powershell
$env:WOKWI_CLI_TOKEN = "your_token_here"
.\run_simulations.ps1
```

**Linux/macOS:**
```bash
export WOKWI_CLI_TOKEN="your_token_here"
./run_simulations.sh
```

---

## Running Tests

### Backend Tests

**Linux/macOS:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest tests/
```

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
pytest tests/
```

### Frontend Tests

```bash
cd dashboards/admin-dashboard
npm install
npm test
```

---

## Common Commands

| Command | Description |
| :--- | :--- |
| `docker-compose up -d` | Start all services |
| `docker-compose down` | Stop all services |
| `docker-compose logs -f api-gateway` | View API logs |
| `docker-compose restart api-gateway` | Restart a service |
| `docker-compose up -d --build` | Rebuild and start services |

## Stopping the System

```bash
docker-compose down
```

To also remove data volumes:

```bash
docker-compose down -v
```

---

## Troubleshooting

### Dashboard shows "ERR_EMPTY_RESPONSE"

The dashboards need time to install npm dependencies on first run. Wait 2-3 minutes, then refresh. Check progress with:

```bash
docker logs -f infant-stack-nurse-dashboard
```

### API returns "Unknown error"

- Ensure PostgreSQL is healthy: `docker-compose ps`
- Restart the stack: `docker-compose down && docker-compose up -d`

### Authentication failures

- Check if Keycloak is fully started (it can take ~60s):
  `docker logs infant-stack-keycloak`
- Ensure the realm was correctly imported.

### Database connection issues

Wait 30 seconds after startup for health checks, then:

```bash
docker-compose restart api-gateway
```

### View service logs

```bash
docker-compose logs -f api-gateway
docker-compose logs -f keycloak
docker-compose logs -f nurse-dashboard
```

### Windows-specific: Docker build fails with "invalid file request"

If you have a local Python `venv` in the `backend` folder, it may cause build errors. The project includes a `.dockerignore` file to handle this automatically. If issues persist, delete the local `venv` folder before building:

```powershell
Remove-Item -Recurse -Force backend\venv
docker-compose up -d --build
```

