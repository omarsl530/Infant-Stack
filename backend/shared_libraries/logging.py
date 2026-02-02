"""
Structured logging configuration using structlog.
"""

import logging
import sys

import structlog


def setup_logging(service_name: str, log_level: str = "INFO") -> None:
    """Configure structured logging for a service.

    Args:
        service_name: Name of the service for log context.
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            (
                structlog.dev.ConsoleRenderer()
                if log_level == "DEBUG"
                else structlog.processors.JSONRenderer()
            ),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Bind service name to all logs
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically module name).

    Returns:
        Configured structlog logger.
    """
    return structlog.get_logger(name)
