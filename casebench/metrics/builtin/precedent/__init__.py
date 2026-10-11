"""The precedent metric: the decisions an answer cites against the court's, as corpus documents."""

from casebench.metrics.authorities import AuthorityMetric


class Metric(AuthorityMetric):
    name = "precedent"
    listed_kind = "decision"
