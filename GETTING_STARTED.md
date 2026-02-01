# Getting Started with Infant-Stack

This guide explains how to run the Infant-Stack hospital infant tracking system locally.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** (to clone the repository)
- Ports 3000, 8000, 5432, 27017, 6379, 1883, 9001 available

## Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Infant-Stack
```

### 2. Start All Services

```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** (port 5432) - Primary database
- **MongoDB** (port 27017) - Time-series logs
- **Redis** (port 6379) - Cache/sessions
- **MQTT Broker** (ports 1883, 9001) - Real-time tag communication
- **API Gateway** (port 8000) - REST API
- **Device Gateway** - MQTT-to-database bridge
- **Nurse Dashboard** (port 3000) - Web interface

### 3. Access the Dashboard

Open your browser to: **http://localhost:3000**

## Verification

Check all services are running:

```bash
docker-compose ps
```

Test the API:

```bash
curl http://localhost:8000/health
```

## Common Commands

| Command | Description |
|---------|-------------|
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
Restart the stack:
```bash
docker-compose down && docker-compose up -d
```

### Database connection issues
Wait 30 seconds after startup for health checks, then:
```bash
docker-compose restart api-gateway
```

### View service logs
```bash
docker logs infant-stack-api-gateway --tail 50
docker logs infant-stack-nurse-dashboard --tail 50
```
