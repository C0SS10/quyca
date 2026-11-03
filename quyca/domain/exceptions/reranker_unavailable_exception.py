class RerankerUnavailableException(Exception):
    """The reranker service is off, does not answer or took longer than the allowed time (the route turns it into a 503)."""
