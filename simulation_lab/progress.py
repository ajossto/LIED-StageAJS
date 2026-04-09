from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable


ProgressCallback = Callable[[dict], None]
CancelCallback = Callable[[], bool]

_progress_callback: ContextVar[ProgressCallback | None] = ContextVar("progress_callback", default=None)
_cancel_callback: ContextVar[CancelCallback | None] = ContextVar("cancel_callback", default=None)


@contextmanager
def progress_reporting(callback: ProgressCallback | None, cancel_callback: CancelCallback | None = None):
    token = _progress_callback.set(callback)
    cancel_token = _cancel_callback.set(cancel_callback)
    try:
        yield
    finally:
        _progress_callback.reset(token)
        _cancel_callback.reset(cancel_token)


def emit_progress(payload: dict) -> None:
    callback = _progress_callback.get()
    if callback is not None:
        callback(payload)


class CancelledByUser(RuntimeError):
    pass


def ensure_not_cancelled() -> None:
    callback = _cancel_callback.get()
    if callback is not None and callback():
        raise CancelledByUser("Simulation interrompue par l'utilisateur.")
