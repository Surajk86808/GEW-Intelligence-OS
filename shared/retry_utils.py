from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential


def retry_on_transient_errors(attempts: int = 3):
    return retry(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        reraise=True,
    )

