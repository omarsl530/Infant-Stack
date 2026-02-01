# Infant-Stack Backend

Backend services for the Infant-Stack hospital infant security ecosystem.

## Services

- **API Gateway** - REST API entry point for frontend clients
- **Device Gateway** - MQTT message handler for IoT tag communication

## Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run API server
uvicorn services.api_gateway.main:app --reload

# Run device gateway
python -m services.device_gateway.main
```

## Testing

```bash
pytest
```
