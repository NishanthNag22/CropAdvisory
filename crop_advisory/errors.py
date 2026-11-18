"""Actionable errors shared by the local model and pipeline stages."""

class AdvisoryError(Exception):
    """An actionable local service or output error."""


class ModelOutputTruncated(AdvisoryError):
    """Incomplete model output; callers may retry, but must never display it."""
    def __init__(self, limit, metrics=None):
        super().__init__(f'Model output reached its {limit}-token limit before completion.')
        self.limit=limit
        self.metrics=metrics or {}
