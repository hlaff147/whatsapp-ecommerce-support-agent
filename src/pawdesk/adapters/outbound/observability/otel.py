"""Configuração de OpenTelemetry para traces distribuídos."""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter


def configure_otel(service_name: str = "pawdesk", otlp_endpoint: str | None = None) -> None:
    """Configura TracerProvider com exportação OTLP (se configurada) ou no-op seguro."""
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if otlp_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    else:
        # Evita ruído no terminal em local; spans ainda existem para correlação
        _ = ConsoleSpanExporter
    trace.set_tracer_provider(provider)


def get_tracer(name: str = "pawdesk") -> trace.Tracer:
    return trace.get_tracer(name)
