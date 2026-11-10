"""Plain data classes shared by the workflow, activities, starter and tests.

One dataclass as the workflow input (not several positional arguments) is the pattern to copy: you can add a field with a default later
without breaking workflows that are already running, and the CLI can send it as one JSON object.
"""
from dataclasses import dataclass


@dataclass
class BatchInput:
    batch_id: str
    cooling_off_seconds: int = 86400      # the "long-running review window" step: one day by default
    approval_timeout_hours: int = 72      # how long we wait for a human before giving up


@dataclass
class BatchResult:
    batch_id: str
    pdfs: int
    irs_reference: str
    approved_by: str
    status: str
