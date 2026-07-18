"""Small process-wide capacity boundaries for local media executors.

The standalone Web App deliberately runs its bounded FFmpeg features in the
request process while it is deployed on a verified single-replica topology.
Those features must share one admission gate: a per-module semaphore would
allow two independent routes to launch FFmpeg at the same time and defeat the
resource limit it appears to provide.
"""

from __future__ import annotations

import threading


MEDIA_FFMPEG_MAX_CONCURRENT = 1
_MEDIA_FFMPEG_CAPACITY = threading.BoundedSemaphore(value=MEDIA_FFMPEG_MAX_CONCURRENT)


def media_ffmpeg_capacity() -> threading.BoundedSemaphore:
    """Return the one process-local FFmpeg execution gate."""

    return _MEDIA_FFMPEG_CAPACITY
