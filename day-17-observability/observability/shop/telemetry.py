"""OpenTelemetry setup: traces and logs go to the collector over OTLP/HTTP.

Everything is driven by standard environment variables so the manifest, not the code, decides where
data goes: OTEL_SERVICE_NAME, OTEL_EXPORTER_OTLP_ENDPOINT, OTEL_RESOURCE_ATTRIBUTES.
If OTEL_EXPORTER_OTLP_ENDPOINT is not set, nothing is exported and the app still works.
"""
import logging
import os

_initialised = False


def init():
    global _initialised
    if _initialised or not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    _initialised = True

    from opentelemetry import trace
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({})  # reads OTEL_SERVICE_NAME and OTEL_RESOURCE_ATTRIBUTES

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(tracer_provider)

    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
    set_logger_provider(logger_provider)
    logging.getLogger().addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))

    from app import app

    FlaskInstrumentor().instrument_app(app)
    RequestsInstrumentor().instrument()
