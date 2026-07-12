"""Compatibility ASGI entrypoint.

Railway runs ``uvicorn app:app``. Keeping ``main:app`` as this alias prevents
an old command from reviving the removed standalone billing/PayOS writer.
"""

from app import app


__all__ = ["app"]
