"""A research question; the answer ranks authorities and sums them up."""


class Task:
    input_fields = ("question", "constraints")
    reference_fields = ("reference answer", "key points", "statutes", "precedents")
    default_metrics = ("authority_recall", "authority_ndcg", "citation_integrity")
