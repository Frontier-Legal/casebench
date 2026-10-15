"""A document and the fields to take from it; the answer is a JSON object of values."""


class Task:
    input_fields = ("document", "fields")
    reference_fields = ("expected",)
    default_metrics = ("fields",)
