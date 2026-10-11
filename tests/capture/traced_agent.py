"""A harness that already exports OpenTelemetry spans, GenAI and OpenInference alike."""

import json

from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter()))
tracer = provider.get_tracer("harness")


def answer(question: str) -> str:
    found = [f"{question}-a", f"{question}-b", f"{question}-c"]
    with tracer.start_as_current_span("retrieve") as span:
        span.set_attribute("openinference.span.kind", "RETRIEVER")
        for n, doc in enumerate(found):
            span.set_attribute(f"retrieval.documents.{n}.document.id", doc)
    with tracer.start_as_current_span("rerank") as span:
        span.set_attribute("openinference.span.kind", "RERANKER")
        for n, doc in enumerate(found):
            span.set_attribute(f"reranker.input_documents.{n}.document.id", doc)
        span.set_attribute("reranker.output_documents.0.document.id", found[0])
    with tracer.start_as_current_span("statutes") as span:
        span.set_attribute("gen_ai.operation.name", "retrieval")
        span.set_attribute("gen_ai.retrieval.documents", json.dumps([{"id": f"{question}-law"}]))
    with tracer.start_as_current_span("memory") as span:
        span.set_attribute("gen_ai.operation.name", "retrieval")
    with tracer.start_as_current_span("chat model-x") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.provider.name", "national")
        span.set_attribute("gen_ai.request.model", "model-x")
        span.set_attribute("gen_ai.usage.input_tokens", 321)
        span.set_attribute("gen_ai.usage.output_tokens", 54)
    return f"answer to {question}"
