"""An instruction and facts; the answer is a document."""


class Task:
    input_fields = ("instruction", "facts", "document")
    reference_fields = ("reference answer", "key points", "statutes", "precedents")
    default_metrics = ("criteria", "citation_integrity")
