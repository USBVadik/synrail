def compute_retry_delay(attempt, base_seconds=2, cap_seconds=30):
    """Return the retry delay in seconds for a 1-indexed attempt."""
    return min(base_seconds ** attempt, cap_seconds)
