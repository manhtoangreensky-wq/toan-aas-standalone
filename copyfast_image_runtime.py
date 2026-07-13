"""Small shared safety boundary for Pillow-backed Web-native operations.

The Web App may have several independent image products (for example Image →
PDF and Resize & Aspect Studio), but their decoders contend for the same
process memory.  This module intentionally shares only a single bounded gate;
database schemas, storage roots and output contracts remain isolated in their
own feature modules.
"""

from __future__ import annotations

import threading


# A decoded 16 MP raster can temporarily require hundreds of MiB while it is
# rotated, resized or blurred.  One process-wide slot prevents two separate
# product routes from each believing their own per-feature semaphore is safe.
IMAGE_DECODER_MAX_CONCURRENT = 1
_IMAGE_DECODER_CAPACITY = threading.BoundedSemaphore(value=IMAGE_DECODER_MAX_CONCURRENT)


def image_decoder_capacity() -> threading.BoundedSemaphore:
    """Return the one shared process-local Pillow decoder gate."""
    return _IMAGE_DECODER_CAPACITY
