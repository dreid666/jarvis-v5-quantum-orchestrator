"""OpenTelemetry instrumentation for JARVIS runtime."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


class OpenTelemetryProvider:
    """Wrapper for OpenTelemetry integration."""

    def __init__(self, service_name: str = "jarvis-v8"):
        self.service_name = service_name
        self.tracer_provider: Optional[Any] = None
        self.meter_provider: Optional[Any] = None
        self.logger_provider: Optional[Any] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize OpenTelemetry providers."""

        if self._initialized:
            return

        try:
            from opentelemetry import metrics, trace
            from opentelemetry.sdk.metrics import MeterProvider
            from opentelemetry.sdk.resources import SERVICE_NAME, Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            try:
                from opentelemetry import _logs as logs_api
                from opentelemetry.sdk._logs import LoggerProvider
            except ImportError:
                logs_api = None
                LoggerProvider = None  # type: ignore[assignment]

            resource = Resource(attributes={SERVICE_NAME: self.service_name})

            self.tracer_provider = TracerProvider(resource=resource)
            try:
                from opentelemetry.exporter.jaeger.thrift import JaegerExporter

                self.tracer_provider.add_span_processor(
                    BatchSpanProcessor(JaegerExporter(agent_host_name="localhost", agent_port=6831))
                )
            except ImportError:
                pass
            trace.set_tracer_provider(self.tracer_provider)

            self.meter_provider = MeterProvider(resource=resource)
            metrics.set_meter_provider(self.meter_provider)

            if logs_api is not None and LoggerProvider is not None:
                self.logger_provider = LoggerProvider(resource=resource)
                logs_api.set_logger_provider(self.logger_provider)

            self._initialized = True
        except ImportError:
            pass

    def get_tracer(self, name: str) -> Any:
        """Get OpenTelemetry tracer."""

        if not self._initialized:
            self.initialize()
        if self.tracer_provider:
            return self.tracer_provider.get_tracer(name)
        return None

    def trace_function(self, name: Optional[str] = None) -> Callable:
        """Decorator to trace function execution."""

        def decorator(func: F) -> F:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                tracer = self.get_tracer(func.__module__)
                span_name = name or func.__qualname__
                if tracer:
                    with tracer.start_as_current_span(span_name) as span:
                        span.set_attribute("function.name", func.__qualname__)
                        span.set_attribute("function.module", func.__module__)
                        return func(*args, **kwargs)
                return func(*args, **kwargs)

            return wrapper  # type: ignore[return-value]

        return decorator

    @contextmanager
    def span(self, name: str, attributes: Optional[dict[str, Any]] = None):
        """Context manager for manual span creation."""

        tracer = self.get_tracer(__name__)
        if tracer:
            with tracer.start_as_current_span(name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                yield span
            return
        yield None


_otel_provider: Optional[OpenTelemetryProvider] = None


def get_otel_provider() -> OpenTelemetryProvider:
    """Get or create global OpenTelemetry provider."""

    global _otel_provider
    if _otel_provider is None:
        _otel_provider = OpenTelemetryProvider()
        _otel_provider.initialize()
    return _otel_provider


__all__ = ["OpenTelemetryProvider", "get_otel_provider"]
