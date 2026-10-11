"""Read an OTLP trace export, protobuf or JSON, into plain spans."""

import json
from dataclasses import dataclass, field
from typing import Any

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.common.v1.common_pb2 import AnyValue

NANOS = 1_000_000_000


@dataclass
class RawSpan:
    trace_id: str
    name: str
    started: float
    ended: float
    attributes: dict[str, Any] = field(default_factory=dict)


def _proto_value(value: AnyValue) -> Any:
    kind = value.WhichOneof("value")
    if kind == "array_value":
        return [_proto_value(item) for item in value.array_value.values]
    if kind == "kvlist_value":
        return {item.key: _proto_value(item.value) for item in value.kvlist_value.values}
    if kind == "bytes_value":
        return value.bytes_value.hex()
    return getattr(value, kind) if kind else None


def from_protobuf(body: bytes) -> list[RawSpan]:
    request = ExportTraceServiceRequest.FromString(body)
    return [
        RawSpan(
            trace_id=span.trace_id.hex(),
            name=span.name,
            started=span.start_time_unix_nano / NANOS,
            ended=span.end_time_unix_nano / NANOS,
            attributes={a.key: _proto_value(a.value) for a in span.attributes},
        )
        for resource in request.resource_spans
        for scope in resource.scope_spans
        for span in scope.spans
    ]


def _json_value(value: dict[str, Any]) -> Any:
    if "arrayValue" in value:
        return [_json_value(item) for item in value["arrayValue"].get("values", [])]
    if "kvlistValue" in value:
        return {i["key"]: _json_value(i["value"]) for i in value["kvlistValue"].get("values", [])}
    if "intValue" in value:
        return int(value["intValue"])  # OTLP/JSON writes 64-bit integers as strings
    for key in ("stringValue", "doubleValue", "boolValue", "bytesValue"):
        if key in value:
            return value[key]
    return None


def from_json(body: bytes) -> list[RawSpan]:
    """OTLP/JSON: ids are hex strings, times are nanoseconds written as strings."""
    request = json.loads(body)
    return [
        RawSpan(
            trace_id=span.get("traceId", "").lower(),
            name=span.get("name", ""),
            started=int(span.get("startTimeUnixNano", 0)) / NANOS,
            ended=int(span.get("endTimeUnixNano", 0)) / NANOS,
            attributes={
                a["key"]: _json_value(a.get("value", {})) for a in span.get("attributes", [])
            },
        )
        for resource in request.get("resourceSpans", [])
        for scope in resource.get("scopeSpans", [])
        for span in scope.get("spans", [])
    ]


def decode(body: bytes, content_type: str) -> list[RawSpan]:
    return from_json(body) if "json" in content_type else from_protobuf(body)
