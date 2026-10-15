"""A question about the law, answered in prose."""


class Task:
    input_fields = ("question", "facts")
    reference_fields = ("reference answer", "key points", "statutes", "precedents")
    default_metrics = ("criteria",)
