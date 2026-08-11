"""Small shared safety boundary for Pillow-backed Web-native operations.

The Web App may have several independent image products (for example Image →
PDF and Resize & Aspect Studio), but their decoders contend for the same
process memory.  This module intentionally shares only a single bounded gate;
database schemas, storage roots and output contracts remain isolated in their
own feature modules.
"""

from __future__ import annotations

from contextlib import contextmanager
import threading
from collections.abc import Iterator


# A decoded 16 MP raster can temporarily require hundreds of MiB while it is
# rotated, resized or blurred.  One process-wide slot prevents two separate
# product routes from each believing their own per-feature semaphore is safe.
IMAGE_DECODER_MAX_CONCURRENT = 1
_IMAGE_DECODER_CAPACITY = threading.BoundedSemaphore(value=IMAGE_DECODER_MAX_CONCURRENT)


class ImageDecoderCapacityBusy(RuntimeError):
    """A decoder-backed request must retry after the shared slot is released."""


def image_decoder_capacity() -> threading.BoundedSemaphore:
    """Return the one shared process-local Pillow decoder gate."""
    return _IMAGE_DECODER_CAPACITY


@contextmanager
def reserve_image_decoder_capacity() -> Iterator[None]:
    """Acquire one Pillow decoder slot without waiting or leaking it on failure."""

    capacity = image_decoder_capacity()
    if not capacity.acquire(blocking=False):
        raise ImageDecoderCapacityBusy("Shared Pillow decoder capacity is busy")
    try:
        yield
    finally:
        capacity.release()
