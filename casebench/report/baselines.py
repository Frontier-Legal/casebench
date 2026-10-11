"""What an outcome suite scores with no legal reasoning at all (decision 0028)."""

from collections import Counter

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import LeaveOneOut, cross_val_predict
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline


def majority_class(labels: list[str]) -> float | None:
    """Accuracy of always answering the suite's most common ruling."""
    if not labels:
        return None
    return Counter(labels).most_common(1)[0][1] / len(labels)


def text_only(texts: list[str], labels: list[str]) -> float | None:
    """Accuracy of guessing the ruling from the facts' words alone, leave-one-out."""
    if len(set(labels)) < 2 or len(labels) < 2:
        return None
    model = make_pipeline(CountVectorizer(), MultinomialNB())
    predicted = cross_val_predict(model, texts, labels, cv=LeaveOneOut())
    return sum(p == t for p, t in zip(predicted, labels, strict=True)) / len(labels)
