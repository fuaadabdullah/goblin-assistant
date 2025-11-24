import logging
import json
import sys
from datetime import datetime
from typing import Dict, Any
import os

class DatadogJSONFormatter(logging.Formatter):
    """JSON formatter for Datadog log ingestion with structured fields."""

    def __init__(self, service_name: str = "goblin-api", env: str = None):
        super().__init__()
        self.service_name = service_name
        self.env = env or os.getenv("DD_ENV", "dev")
        self.host = os.getenv("DD_HOST", os.uname().nodename if hasattr(os, 'uname') else 'unknown')

    def format(self, record: logging.LogRecord) -> str:
        # Extract trace and span IDs if available (from ddtrace)
        trace_id = getattr(record, 'dd.trace_id', None)
        span_id = getattr(record, 'dd.span_id', None)

        # Build structured log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "service": self.service_name,
            "env": self.env,
            "host": self.host,
            "msg": record.getMessage(),
        }

        # Add trace context if available
        if trace_id is not None:
            log_entry["trace_id"] = str(trace_id)
        if span_id is not None:
            log_entry["span_id"] = str(span_id)

        # Add extra fields from record
        if hasattr(record, 'context') and record.context:
            log_entry.update(record.context)

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging(
    level: str = "INFO",
    service_name: str = "goblin-api",
    env: str = None,
    enable_console: bool = True,
    enable_file: bool = False,
    log_file: str = None
) -> logging.Logger:
    """Setup structured logging for Datadog integration."""

    # Create logger
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # JSON formatter for Datadog
    formatter = DatadogJSONFormatter(service_name, env)

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler (optional)
    if enable_file and log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Prevent duplicate logs from parent loggers
    logger.propagate = False

    return logger


# Global logger instance
logger = setup_logging()
