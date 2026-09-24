"""Comprehensive structured logging for JARVIS.

Implements structured logging with audit trails, performance metrics,
and diagnostic information for troubleshooting and monitoring.
"""

from __future__ import annotations

import copy
import json
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from jarvis.security.audit import _sanitize


class LogLevel(str, Enum):
    """Standard logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AuditEvent:
    """Structured audit trail event."""

    def __init__(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        from datetime import timezone

        self.event_id = str(uuid4())
        self.event_type = event_type
        self.user_id = user_id
        self.action = action
        self.resource = resource
        self.result = result
        self.details = copy.deepcopy(_sanitize(details or {}))
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""

        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "details": copy.deepcopy(self.details),
            "timestamp": self.timestamp.isoformat(),
        }


class StructuredLogger:
    """Logger with structured output and audit trail support."""

    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.audit_trail: List[Dict[str, Any]] = []
        self._setup_formatter()

    def _setup_formatter(self) -> None:
        """Configure JSON structured logging format."""

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(handler)

    def log_structured(self, level: LogLevel, message: str, **fields: Any) -> None:
        """Log structured event with custom fields."""

        from datetime import datetime, timezone

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "logger": self.name,
            "message": message,
            **fields,
        }
        getattr(self.logger, level.value.lower())(json.dumps(log_entry))

    def log_audit(self, event: AuditEvent) -> None:
        """Record audit event."""

        event_record = event.to_dict()
        self.audit_trail.append(copy.deepcopy(event_record))
        self.log_structured(LogLevel.INFO, f"Audit: {event.event_type}", audit_event=copy.deepcopy(event_record))

    def log_performance(
        self,
        operation: str,
        duration_ms: float,
        status: str = "success",
        **details: Any,
    ) -> None:
        """Log performance metrics for an operation."""

        self.log_structured(
            LogLevel.INFO,
            f"Performance: {operation}",
            operation=operation,
            duration_ms=round(duration_ms, 2),
            status=status,
            **details,
        )

    @contextmanager
    def timed_operation(self, operation: str, **details: Any):
        """Context manager for timing operations."""

        start_time = time.time()
        try:
            yield
            duration_ms = (time.time() - start_time) * 1000
            self.log_performance(operation, duration_ms, status="success", **details)
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000
            self.log_performance(operation, duration_ms, status="error", error=str(exc), **details)
            raise

    def debug(self, message: str, **fields: Any) -> None:
        """Log debug message."""

        self.log_structured(LogLevel.DEBUG, message, **fields)

    def info(self, message: str, **fields: Any) -> None:
        """Log info message."""

        self.log_structured(LogLevel.INFO, message, **fields)

    def warning(self, message: str, **fields: Any) -> None:
        """Log warning message."""

        self.log_structured(LogLevel.WARNING, message, **fields)

    def error(self, message: str, **fields: Any) -> None:
        """Log error message."""

        self.log_structured(LogLevel.ERROR, message, **fields)

    def critical(self, message: str, **fields: Any) -> None:
        """Log critical message."""

        self.log_structured(LogLevel.CRITICAL, message, **fields)

    def get_audit_trail(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get audit trail events."""

        events = self.audit_trail[-limit:] if limit else self.audit_trail
        return copy.deepcopy(events)


def trace_calls(logger: StructuredLogger) -> Callable:
    """Decorator to trace function calls."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            func_name = func.__qualname__
            with logger.timed_operation(f"call:{func_name}", args_count=len(args), kwargs_keys=list(kwargs.keys())):
                return func(*args, **kwargs)

        return wrapper

    return decorator


_default_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """Get or create a logger instance."""

    if name not in _default_loggers:
        _default_loggers[name] = StructuredLogger(name)
    return _default_loggers[name]


__all__ = ["LogLevel", "AuditEvent", "StructuredLogger", "trace_calls", "get_logger"]
