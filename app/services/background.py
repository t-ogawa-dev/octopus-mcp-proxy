"""
Bounded background executor for fire-and-forget work such as log writes
"""

import logging
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


class BoundedExecutor:
    """ThreadPoolExecutor that drops work instead of queueing without limit.

    Log writes must never let a burst of requests (for example unauthenticated
    traffic) grow memory without bound, so submissions beyond max_pending are dropped.
    """

    def __init__(self, max_workers: int, max_pending: int, name: str):
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix=name)
        self._slots = threading.BoundedSemaphore(max_pending)
        self._name = name

    def submit(self, fn: Callable[..., Any], *args: Any) -> Future | None:
        if not self._slots.acquire(blocking=False):
            logger.warning("%s queue is full; dropping background task", self._name)
            return None
        future = self._pool.submit(fn, *args)
        future.add_done_callback(lambda _future: self._slots.release())
        return future

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)
