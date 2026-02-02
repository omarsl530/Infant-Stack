# Infant-Stack Backend

Backend services for the Infant-Stack hospital infant security ecosystem.

## Services

- **API Gateway** - REST API entry point for frontend clients
- **Device Gateway** - MQTT message handler for IoT tag communication

## Development

```bash
# Setup environment
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Linting & Formatting
black .
ruff check .
mypy .

# Run API server
uvicorn services.api_gateway.main:app --reload

# Run device gateway
python -m services.device_gateway.main
```

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=services tests/
```
