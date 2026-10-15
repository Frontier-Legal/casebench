"""The facts of a decision without its ruling; the answer names the ruling."""


class Task:
    input_fields = ("question", "facts")
    reference_fields = ("outcome",)
    default_metrics = ("outcome",)
