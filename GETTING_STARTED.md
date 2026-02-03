# Getting Started with Infant-Stack

This guide explains how to run the Infant-Stack hospital infant tracking system locally.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** (to clone the repository)
- **Node.js 20+** (if running dashboards locally without Docker)
- Ports **3000-3002**, **8000**, **8080**, **5432**, **27017**, **6379**, **1883**, **9001** available

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/omarsl530/Infant-Stack.git
cd Infant-Stack
```

### 2. Configure Environment

Copy the example environment file:

```bash
cp .env.example .env
```

### 3. Start All Services

```bash
docker-compose up -d
```

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
- **Default Password**: `admin` (or `admin123` if specified in `.env`)

## Verification

Check all services are running:

```bash
docker-compose ps
```

Test the API:

```bash
curl http://localhost:8000/health
```

## Running Tests

### Backend Tests

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest tests/
```

### Frontend Tests

```bash
cd dashboards/admin-dashboard
npm install
npm test
```

## Common Commands

| Command | Description |
| :--- | :--- |
| `docker-compose up -d` | Start all services |
| `docker-compose down` | Stop all services |
| `docker-compose logs -f api-gateway` | View API logs |
| `docker-compose restart api-gateway` | Restart a service |

## Stopping the System

```bash
docker-compose down
```

To also remove data volumes:

```bash
docker-compose down -v
```

## Troubleshooting

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
