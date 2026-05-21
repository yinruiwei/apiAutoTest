"""PDA-specific extension functions."""

from __future__ import annotations


def build_pick_payload(task_no: str, picker: str = '') -> dict:
    """Build a PDA pick confirmation payload."""
    return {'task_no': task_no, 'picker': picker}
