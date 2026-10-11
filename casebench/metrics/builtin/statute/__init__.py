"""The statute metric: the statutes an answer cites against the court's, as corpus documents."""

from casebench.metrics.authorities import AuthorityMetric


class Metric(AuthorityMetric):
    name = "statute"
    listed_kind = "statute"
