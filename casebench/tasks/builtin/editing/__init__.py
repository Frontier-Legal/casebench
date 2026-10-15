"""A document and an instruction; the answer is the edited document."""


class Task:
    input_fields = ("instruction", "document")
    reference_fields = ("issues", "key points")
    default_metrics = ("issues_found", "edit_preservation")
