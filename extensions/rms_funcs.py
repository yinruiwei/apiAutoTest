"""RMS-specific extension functions."""

from __future__ import annotations

from collections.abc import Callable
from time import sleep


def wait_rms_task_status(
    query_func: Callable[[str], dict],
    task_no: str,
    expected_status: str,
    timeout_seconds: int = 60,
    interval_seconds: int = 3,
) -> dict:
    """Poll an RMS task until it reaches the expected status."""
    attempts = max(timeout_seconds // interval_seconds, 1)
    last_response: dict = {}
    for _ in range(attempts):
        last_response = query_func(task_no)
        data = last_response.get('data') or {}
        if data.get('status') == expected_status:
            return last_response
        sleep(interval_seconds)
    raise TimeoutError(f'RMS task {task_no} did not reach {expected_status}: {last_response}')
