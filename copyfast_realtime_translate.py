"""Canonical Web App Realtime Gateway & WebSocket Router (RT-02 / RT-FIX1).

Governed by owner-governed-codex, locked-focus-engineering.
Enforces:
1. Account Authority: Strict authentication via require_account. No guest_user fallback.
2. Token Security: Fail-closed on missing REALTIME_STREAM_SECRET. Binds session_id, owner_id, device_id, expires_at, nonce.
3. Owner Isolation: Every REST route and WebSocket verifies session ownership (FOREIGN_OWNER_BLOCKED).
4. Full route family:
   - POST /api/v1/live-translate/sessions
   - GET  /api/v1/live-translate/sessions/{session_id}
   - POST /api/v1/live-translate/sessions/{session_id}/stop
   - GET  /api/v1/live-translate/sessions/{session_id}/export
   - WS   /api/v1/live-translate/sessions/{session_id}/stream
5. Monotonic sequence handling, server ACK, and reconnect support.
"""

from __future__ import annotations

import base64
import enum
import hashlib
import hmac
import io
import json
import logging
import math
import os
import struct
import time
import uuid
import wave
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    from fastapi import APIRouter, Depends, HTTPException, Query, Request, WebSocket, WebSocketDisconnect, status
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    def Field(default=None, **kwargs):
        return default
    class APIRouter:
        def __init__(self, *args, **kwargs):
            self.prefix = kwargs.get("prefix", "")
            self.tags = kwargs.get("tags", [])
            self.routes = []
        def post(self, path, *args, **kwargs):
            def decorator(f):
                self.routes.append(("POST", self.prefix + path, f))
                return f
            return decorator
        def get(self, path, *args, **kwargs):
            def decorator(f):
                self.routes.append(("GET", self.prefix + path, f))
                return f
            return decorator
        def websocket(self, path, *args, **kwargs):
            def decorator(f):
                self.routes.append(("WS", self.prefix + path, f))
                return f
            return decorator
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str = ""):
            super().__init__(f"{status_code}: {detail}")
            self.status_code = status_code
            self.detail = detail
    class WebSocketDisconnect(Exception):
        pass
    class Request: pass
    class WebSocket: pass
    def Query(default=None, **kwargs):
        return default
    def Depends(dependency=None):
        return dependency
    class _Status:
        HTTP_400_BAD_REQUEST = 400
        HTTP_401_UNAUTHORIZED = 401
        HTTP_402_PAYMENT_REQUIRED = 402
        HTTP_403_FORBIDDEN = 403
        HTTP_404_NOT_FOUND = 404
        HTTP_422_UNPROCESSABLE_ENTITY = 422
        HTTP_500_INTERNAL_SERVER_ERROR = 500
        HTTP_503_SERVICE_UNAVAILABLE = 503
    status = _Status()

try:
    from copyfast_auth import require_account
except Exception:
    def require_account(request: Request) -> dict:
        user_id = getattr(getattr(request, "state", None), "user_id", None)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yêu cầu đăng nhập tài khoản TOAN AAS")
        return {"id": user_id, "account_id": user_id, "role": "user"}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/live-translate", tags=["TOAN AAS Live Translate & Dub"])

# Product & Authority Invariants
PRICING_STATE: str = "OWNER_DECISION_REQUIRED"
PRODUCTION_PAID_ADMISSION: str = "FAIL_CLOSED"
PROCESS_RESTART_DURABILITY: str = "NOT_SUPPORTED"
FALSE_ZERO_XU_SETTLEMENT: str = "REMOVED"
TOKEN_TTL_SECONDS: int = 300  # 5 minutes


class RealtimeSessionState(str, enum.Enum):
    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    ERROR = "error"


class RealtimeTranslateMode(str, enum.Enum):
    CAPTION_ONLY = "CAPTION_ONLY"
    CAPTION_TRANSLATE = "CAPTION_TRANSLATE"
    LIVE_DUB = "LIVE_DUB"
    LIVE_DUB_BILINGUAL = "LIVE_DUB_BILINGUAL"


VALID_SESSION_TRANSITIONS: Dict[RealtimeSessionState, Set[RealtimeSessionState]] = {
    RealtimeSessionState.CREATED: {RealtimeSessionState.ACTIVE, RealtimeSessionState.ERROR, RealtimeSessionState.ENDED},
    RealtimeSessionState.ACTIVE: {RealtimeSessionState.PAUSED, RealtimeSessionState.ENDED, RealtimeSessionState.ERROR},
    RealtimeSessionState.PAUSED: {RealtimeSessionState.ACTIVE, RealtimeSessionState.ENDED, RealtimeSessionState.ERROR},
    RealtimeSessionState.ENDED: {RealtimeSessionState.ENDED},
    RealtimeSessionState.ERROR: {RealtimeSessionState.ERROR, RealtimeSessionState.ENDED},
}


@dataclass
class RealtimeSessionConfig:
    owner_id: str
    source_language: str = "auto"
    target_language: str = "vi"
    mode: RealtimeTranslateMode = RealtimeTranslateMode.LIVE_DUB_BILINGUAL
    voice_profile_id: Optional[str] = None
    gender_preference: Optional[str] = "male"
    client_device_id: Optional[str] = None
    metering_block_seconds: int = 60


@dataclass
class RealtimeTranscriptSegment:
    segment_id: str
    sequence: int
    start_ms: int
    end_ms: int
    source_text: str
    translated_text: str = ""
    is_final: bool = False
    speaker_id: Optional[str] = None
    tts_audio_base64: Optional[str] = None
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


class RealtimeTranslateSession:
    """Core state machine and event coordinator for a live translate/dub session."""

    def __init__(self, session_id: str, config: RealtimeSessionConfig):
        self.session_id: str = session_id or str(uuid.uuid4())
        self.config: RealtimeSessionConfig = config
        self.state: RealtimeSessionState = RealtimeSessionState.CREATED
        self.created_at: float = time.time()
        self.started_at: Optional[float] = None
        self.ended_at: Optional[float] = None

        self.last_client_seq: int = 0
        self.last_processed_seq: int = 0
        self.last_ack_seq: int = 0
        self.received_seq_set: Set[int] = set()
        self.buffered_seq_set: Set[int] = set()
        self.processed_seq_set: Set[int] = set()
        self.rejected_seq_set: Set[int] = set()
        self.pending_retry_segments: Dict[int, Any] = {}

        self.total_audio_ms: int = 0
        self.last_metered_seconds: int = 0
        self.consumed_blocks: int = 0
        self.settled_blocks: int = 0
        self.settled_xu: int = 0

        self.segments: List[RealtimeTranscriptSegment] = []
        self.error_message: Optional[str] = None

        self.current_socket_lease: int = 0
        self.active_websocket: Optional[Any] = None
        self.in_flight_segments: Set[str] = set()

    def acquire_socket_lease(self, websocket: Any = None) -> int:
        """Acquires a new monotonic socket generation lease for this session.
        Supersedes any prior socket connection to prevent stale socket overlap.
        """
        self.current_socket_lease += 1
        self.active_websocket = websocket
        return self.current_socket_lease

    def is_socket_lease_active(self, lease_id: int) -> bool:
        """Returns True if the given lease_id is the active generation."""
        return lease_id > 0 and lease_id == self.current_socket_lease

    def start(self) -> None:
        if self.state == RealtimeSessionState.ACTIVE:
            return
        if self.state == RealtimeSessionState.PAUSED:
            self.resume()
            return
        self._transition_to(RealtimeSessionState.ACTIVE)
        if self.started_at is None:
            self.started_at = time.time()

    def pause(self) -> None:
        self._transition_to(RealtimeSessionState.PAUSED)

    def resume(self) -> None:
        self._transition_to(RealtimeSessionState.ACTIVE)

    def end(self) -> None:
        """Idempotently finalizes the session. Safe to call multiple times or after error."""
        if self.state == RealtimeSessionState.ENDED:
            return
        self._transition_to(RealtimeSessionState.ENDED)
        if self.ended_at is None:
            self.ended_at = time.time()

    def fail(self, error_message: str) -> None:
        """Idempotently marks session as ERROR. Safe to call multiple times."""
        if self.state in (RealtimeSessionState.ENDED, RealtimeSessionState.ERROR):
            if not self.error_message:
                self.error_message = error_message
            return
        self.error_message = error_message
        self._transition_to(RealtimeSessionState.ERROR)
        if self.ended_at is None:
            self.ended_at = time.time()

    def _transition_to(self, new_state: RealtimeSessionState) -> None:
        if new_state not in VALID_SESSION_TRANSITIONS.get(self.state, set()):
            raise ValueError(f"Invalid session state transition: {self.state} -> {new_state}")
        self.state = new_state

    def accept_audio_sequence(self, seq: int, duration_ms: int = 0) -> bool:
        """Enforces monotonic client sequence and deduplication.

        Strictly separates:
        1. RECEIVED/IN_FLIGHT: tracks sequences received/in-flight (retryable upon transient failure).
        2. BUFFERED: sequences stored in ingress buffer awaiting VAD segment boundary.
        3. PROCESSED/ACKED: sequences already successfully processed by Bot return False (duplicate_ignored).
        4. REJECTED: sequences permanently rejected by server authority return False.
        5. processed_seq_set / last_processed_seq / last_ack_seq ONLY advance after BOT_BRIDGE_SUCCESS.
        """
        if self.state not in (RealtimeSessionState.ACTIVE, RealtimeSessionState.CREATED):
            return False
        if seq <= 0:
            return False
        if seq in self.processed_seq_set or seq in self.rejected_seq_set or seq <= self.last_processed_seq:
            return False

        if seq not in self.received_seq_set:
            self.received_seq_set.add(seq)
            self.total_audio_ms += max(0, duration_ms)
        self.last_client_seq = max(self.last_client_seq, seq)
        return True

    def mark_sequence_buffered(self, seq: int) -> None:
        """Tracks sequences buffered in ingress awaiting segment boundary.
        DOES NOT advance last_processed_seq, last_ack_seq, or processed_seq_set.
        """
        self.buffered_seq_set.add(seq)

    def add_pending_retry_segment(self, segment: Any) -> None:
        """Stores a speech segment across its entire covered sequence range [sequence_start..sequence_end]
        so that replay of any sequence inside that range reuses the stored segment without re-ingesting PCM.
        """
        seq_start = getattr(segment, "sequence_start", 0)
        seq_end = getattr(segment, "sequence_end", 0)
        if seq_start > 0 and seq_end >= seq_start:
            for s in range(seq_start, seq_end + 1):
                self.pending_retry_segments[s] = segment
        else:
            seq = getattr(segment, "sequence", 0)
            if seq > 0:
                self.pending_retry_segments[seq] = segment

    def mark_range_processed(self, seq_start: int, seq_end: int) -> int:
        """Closes the entire covered sequence range [seq_start..seq_end] upon BOT_BRIDGE_SUCCESS.
        Advances last_processed_seq and last_ack_seq cumulatively to seq_end.
        """
        if seq_start > 0 and seq_end >= seq_start:
            for s in range(seq_start, seq_end + 1):
                self.processed_seq_set.add(s)
                self.buffered_seq_set.discard(s)
                self.pending_retry_segments.pop(s, None)
            self.last_processed_seq = max(self.last_processed_seq, seq_end)
        else:
            self.processed_seq_set.add(seq_end)
            self.buffered_seq_set.discard(seq_end)
            self.pending_retry_segments.pop(seq_end, None)
            self.last_processed_seq = max(self.last_processed_seq, seq_end)

        self.last_ack_seq = self.last_processed_seq
        return self.last_ack_seq

    def mark_range_rejected(self, seq_start: int, seq_end: int) -> None:
        """Marks the entire covered sequence range [seq_start..seq_end] rejected by server authority.
        Prevents any sequence in the range from being re-ingested or processed.
        """
        if seq_start > 0 and seq_end >= seq_start:
            for s in range(seq_start, seq_end + 1):
                self.rejected_seq_set.add(s)
                self.buffered_seq_set.discard(s)
                self.pending_retry_segments.pop(s, None)
        else:
            self.rejected_seq_set.add(seq_end)
            self.buffered_seq_set.discard(seq_end)
            self.pending_retry_segments.pop(seq_end, None)

    def mark_sequence_processed(self, seq: int) -> int:
        """Advances processed/acked state strictly upon BOT_BRIDGE_SUCCESS."""
        return self.mark_range_processed(seq, seq)

    def mark_sequence_rejected(self, seq: int) -> None:
        """Records permanent rejection without marking as Bot success."""
        self.mark_range_rejected(seq, seq)

    def is_sequence_processed(self, seq: int) -> bool:
        return seq in self.processed_seq_set or (seq <= self.last_processed_seq and seq > 0)

    def is_sequence_buffered(self, seq: int) -> bool:
        return seq in self.buffered_seq_set and seq not in self.processed_seq_set

    def is_sequence_in_flight(self, seq: int) -> bool:
        return seq in self.received_seq_set and seq not in self.processed_seq_set and seq not in self.rejected_seq_set

    def handle_reconnect(self, client_last_ack_seq: int) -> Dict[str, Any]:
        return {
            "reconnected": True,
            "session_id": self.session_id,
            "server_last_ack_seq": self.last_processed_seq,
            "client_last_ack_seq": client_last_ack_seq,
            "state": self.state.value,
        }

    def compute_pending_metering_blocks(self) -> int:
        total_seconds = self.total_audio_ms // 1000
        block_sec = max(1, self.config.metering_block_seconds)
        current_blocks = total_seconds // block_sec
        new_blocks = current_blocks - self.consumed_blocks
        if new_blocks > 0:
            self.consumed_blocks = current_blocks
            self.last_metered_seconds = current_blocks * block_sec
            return new_blocks
        return 0

    def settle_blocks(self, block_count: int, xu_per_block: int = 0) -> Dict[str, Any]:
        """Settles accrued blocks exactly once and returns settlement truth.

        Disallows zero-xu settlement under OWNER_DECISION_REQUIRED (FALSE_ZERO_XU_SETTLEMENT=REMOVED).
        """
        if block_count <= 0:
            return {
                "settled": False,
                "settled_blocks": self.settled_blocks,
                "xu_consumed": self.settled_xu,
            }
        if PRICING_STATE == "OWNER_DECISION_REQUIRED" and xu_per_block == 0:
            return {
                "settled": False,
                "blocks_pending": block_count,
                "pricing_state": PRICING_STATE,
                "xu_charged": 0,
                "total_xu_consumed": self.settled_xu,
                "reason": "PRICING_STATE=OWNER_DECISION_REQUIRED; zero xu settlement disallowed",
            }
        self.settled_blocks += block_count
        charge = block_count * max(0, xu_per_block)
        self.settled_xu += charge
        return {
            "settled": True,
            "blocks_settled": block_count,
            "total_settled_blocks": self.settled_blocks,
            "total_settled_seconds": self.settled_blocks * self.config.metering_block_seconds,
            "xu_charged": charge,
            "total_xu_consumed": self.settled_xu,
        }

    def get_telemetry_usage(self) -> Dict[str, Any]:
        """Returns telemetry usage update without claiming canonical Xu settlement."""
        total_seconds = self.total_audio_ms // 1000
        block_sec = max(1, self.config.metering_block_seconds)
        current_blocks = total_seconds // block_sec
        return {
            "type": "usage.updated",
            "audio_ms": self.total_audio_ms,
            "total_seconds": total_seconds,
            "pending_blocks": current_blocks - self.settled_blocks,
            "settled": False,
            "pricing_state": PRICING_STATE,
        }

    def add_segment(self, segment: RealtimeTranscriptSegment) -> None:
        self.segments.append(segment)

    def export_srt(self, requesting_owner_id: str) -> str:
        if str(requesting_owner_id).strip() != str(self.config.owner_id).strip():
            raise PermissionError("Forbidden: requesting owner does not match session owner")

        lines = []
        idx = 1
        for seg in self.segments:
            if not seg.is_final:
                continue
            text = seg.translated_text if seg.translated_text else seg.source_text
            if not text.strip():
                continue
            start_str = self._format_srt_time(seg.start_ms)
            end_str = self._format_srt_time(seg.end_ms)
            lines.append(f"{idx}\n{start_str} --> {end_str}\n{text}\n")
            idx += 1
        return "\n".join(lines)

    def export_vtt(self, requesting_owner_id: str) -> str:
        if str(requesting_owner_id).strip() != str(self.config.owner_id).strip():
            raise PermissionError("Forbidden: requesting owner does not match session owner")

        lines = ["WEBVTT", ""]
        for seg in self.segments:
            if not seg.is_final:
                continue
            text = seg.translated_text if seg.translated_text else seg.source_text
            if not text.strip():
                continue
            start_str = self._format_vtt_time(seg.start_ms)
            end_str = self._format_vtt_time(seg.end_ms)
            lines.append(f"{start_str} --> {end_str}\n{text}\n")
        return "\n".join(lines)

    @staticmethod
    def _format_srt_time(ms: int) -> str:
        s, msec = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d},{msec:03d}"

    @staticmethod
    def _format_vtt_time(ms: int) -> str:
        s, msec = divmod(ms, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}.{msec:03d}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "owner_id": self.config.owner_id,
            "state": self.state.value,
            "mode": self.config.mode.value,
            "source_language": self.config.source_language,
            "target_language": self.config.target_language,
            "voice_profile_id": self.config.voice_profile_id,
            "gender_preference": self.config.gender_preference,
            "total_audio_ms": self.total_audio_ms,
            "consumed_blocks": self.consumed_blocks,
            "settled_blocks": self.settled_blocks,
            "settled_xu": self.settled_xu,
            "last_processed_seq": self.last_processed_seq,
            "last_ack_seq": self.last_ack_seq,
            "segment_count": len([s for s in self.segments if s.is_final]),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "error_message": self.error_message,
            "pricing_state": PRICING_STATE,
            "production_paid_admission": PRODUCTION_PAID_ADMISSION,
            "process_restart_durability": PROCESS_RESTART_DURABILITY,
        }


@dataclass
class SpeechSegment:
    segment_id: str
    sequence_start: int
    sequence_end: int
    start_ms: int
    end_ms: int
    pcm_bytes: bytes
    is_silence: bool = False

    @property
    def duration_ms(self) -> int:
        return max(0, self.end_ms - self.start_ms)

    def to_wav_bytes(self, sample_rate: int = 16000, channels: int = 1, sample_width: int = 2) -> bytes:
        out = io.BytesIO()
        with wave.open(out, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(sample_rate)
            wf.writeframes(self.pcm_bytes)
        return out.getvalue()


class RealtimeAudioIngressBuffer:
    def __init__(
        self,
        sample_rate: int = 16000,
        silence_threshold_rms: float = 350.0,
        silence_duration_trigger_ms: int = 600,
        min_speech_duration_ms: int = 600,
        max_segment_duration_ms: int = 7000,
    ):
        self.sample_rate = sample_rate
        self.bytes_per_second = sample_rate * 2
        self.silence_threshold_rms = silence_threshold_rms
        self.silence_duration_trigger_ms = silence_duration_trigger_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        self.max_segment_duration_ms = max_segment_duration_ms

        self._current_pcm: bytearray = bytearray()
        self._segment_start_ms: int = 0
        self._current_ms: int = 0
        self._seq_start: int = 0
        self._last_seq: int = 0
        self._silence_ms_accum: int = 0
        self._segment_counter: int = 0
        self._has_speech_in_current: bool = False

    @staticmethod
    def calculate_rms(pcm_bytes: bytes) -> float:
        if not pcm_bytes:
            return 0.0
        num_samples = len(pcm_bytes) // 2
        if num_samples == 0:
            return 0.0
        format_str = f"<{num_samples}h"
        samples = struct.unpack(format_str, pcm_bytes[: num_samples * 2])
        sum_squares = sum(s * s for s in samples)
        mean_square = sum_squares / num_samples
        return math.sqrt(mean_square)

    def push_chunk(
        self,
        seq: int,
        pcm_bytes: bytes,
        timestamp_ms: Optional[int] = None,
    ) -> List[SpeechSegment]:
        if not pcm_bytes:
            return []
        aligned_len = len(pcm_bytes) - (len(pcm_bytes) % 2)
        if aligned_len <= 0:
            return []
        valid_bytes = pcm_bytes[:aligned_len]
        chunk_duration_ms = int((aligned_len / self.bytes_per_second) * 1000)

        if self._current_ms == 0 and timestamp_ms is not None:
            self._segment_start_ms = timestamp_ms
            self._current_ms = timestamp_ms
            self._seq_start = seq
        elif timestamp_ms is not None:
            self._current_ms = timestamp_ms

        if len(self._current_pcm) == 0 or self._seq_start == 0:
            self._seq_start = seq
        self._last_seq = seq

        rms = self.calculate_rms(valid_bytes)
        is_chunk_silent = rms < self.silence_threshold_rms

        if not is_chunk_silent:
            self._has_speech_in_current = True
            self._silence_ms_accum = 0
        else:
            self._silence_ms_accum += chunk_duration_ms

        self._current_pcm.extend(valid_bytes)
        self._current_ms += chunk_duration_ms
        current_dur_ms = self._current_ms - self._segment_start_ms

        segments_to_emit: List[SpeechSegment] = []
        hit_silence_boundary = (
            self._has_speech_in_current
            and self._silence_ms_accum >= self.silence_duration_trigger_ms
            and current_dur_ms >= self.min_speech_duration_ms
        )
        hit_max_duration = current_dur_ms >= self.max_segment_duration_ms

        if hit_silence_boundary or hit_max_duration:
            segment = self._emit_current_segment()
            if segment:
                segments_to_emit.append(segment)

        return segments_to_emit

    def clear_partial(self) -> None:
        """Clears partial un-emitted audio in ingress to prevent duplication on reconnect replay."""
        self._current_pcm.clear()
        self._seq_start = 0
        self._has_speech_in_current = False
        self._silence_ms_accum = 0

    def flush(self) -> Optional[SpeechSegment]:
        if len(self._current_pcm) > 0 and self._has_speech_in_current:
            return self._emit_current_segment()
        self._current_pcm.clear()
        self._seq_start = 0
        self._has_speech_in_current = False
        return None

    def _emit_current_segment(self) -> Optional[SpeechSegment]:
        if not self._current_pcm:
            return None
        self._segment_counter += 1
        seg_id = f"seg_{self._segment_counter:04d}"
        pcm_data = bytes(self._current_pcm)

        segment = SpeechSegment(
            segment_id=seg_id,
            sequence_start=self._seq_start,
            sequence_end=self._last_seq,
            start_ms=self._segment_start_ms,
            end_ms=self._current_ms,
            pcm_bytes=pcm_data,
            is_silence=not self._has_speech_in_current,
        )

        self._current_pcm.clear()
        self._segment_start_ms = self._current_ms
        self._seq_start = 0
        self._silence_ms_accum = 0
        self._has_speech_in_current = False
        return segment


# In-memory registry for active sessions
_ACTIVE_SESSIONS: Dict[str, RealtimeTranslateSession] = {}
_ACTIVE_INGRESS_BUFFERS: Dict[str, RealtimeAudioIngressBuffer] = {}


def get_stream_secret() -> str:
    """Retrieves secret for signing stream tokens. FAILS CLOSED if not set."""
    secret = os.environ.get("REALTIME_STREAM_SECRET", "").strip()
    if not secret or len(secret) < 16:
        raise RuntimeError("REALTIME_STREAM_SECRET_NOT_CONFIGURED")
    return secret


def generate_stream_token(
    session_id: str,
    owner_id: str,
    device_id: str,
    expires_at: int,
    nonce: Optional[str] = None,
) -> str:
    secret = get_stream_secret()
    nonce_val = nonce or uuid.uuid4().hex[:8]
    payload = f"{session_id}:{owner_id}:{device_id}:{expires_at}:{nonce_val}"
    signature = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    token_data = {
        "session_id": session_id,
        "owner_id": owner_id,
        "device_id": device_id,
        "exp": expires_at,
        "nonce": nonce_val,
        "sig": signature,
    }
    return base64.urlsafe_b64encode(json.dumps(token_data).encode("utf-8")).decode("ascii")


def verify_stream_token(token: str, session_id: str) -> Optional[Tuple[str, str]]:
    try:
        secret = get_stream_secret()
        token_clean = token.strip()
        trans = token_clean.replace("-", "+").replace("_", "/")
        raw_bytes = base64.b64decode(trans.encode("ascii"), validate=True)
        raw = raw_bytes.decode("utf-8")
        data = json.loads(raw)
        if data.get("session_id") != session_id:
            return None
        if time.time() > data.get("exp", 0):
            return None
        nonce_val = data.get("nonce", "")
        device_id = data.get("device_id", "")
        owner_id = data.get("owner_id", "")
        payload = f"{data['session_id']}:{owner_id}:{device_id}:{data['exp']}:{nonce_val}"
        expected_sig = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if hmac.compare_digest(data.get("sig", ""), expected_sig):
            return str(owner_id), str(device_id)
    except Exception:
        return None
    return None


_TEST_PRICING_ADMISSION_OVERRIDE: Optional[Callable[[RealtimeTranslateMode], bool]] = None


def set_test_pricing_admission_override(override: Optional[Callable[[RealtimeTranslateMode], bool]]) -> None:
    """Sets a server-side test authority for pricing admission in provider-free tests."""
    global _TEST_PRICING_ADMISSION_OVERRIDE
    _TEST_PRICING_ADMISSION_OVERRIDE = override


def is_pricing_admission_allowed(mode: RealtimeTranslateMode) -> bool:
    """Determines whether realtime session admission is allowed.

    Fails closed on production paid modes until Owner approves prices.
    Never allows environment or client bypass in production environment.
    """
    if PRODUCTION_PAID_ADMISSION != "FAIL_CLOSED":
        return True

    env_name = (
        os.environ.get("ENV")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("TOAN_AAS_ENV")
        or ""
    ).lower()
    is_production = env_name in ("production", "prod", "live")
    if is_production:
        return False

    if _TEST_PRICING_ADMISSION_OVERRIDE is not None:
        return bool(_TEST_PRICING_ADMISSION_OVERRIDE(mode))

    is_test_env = (
        os.environ.get("ENV") == "test"
        or os.environ.get("TESTING") == "1"
        or os.environ.get("CI") == "true"
        or os.environ.get("PYTEST_CURRENT_TEST") is not None
    )
    if is_test_env and os.environ.get("REALTIME_ALLOW_UNPRICED_TEST_SESSION") == "1":
        return True

    return False


class CreateSessionRequest(BaseModel):
    source_language: str = Field(default="auto", description="Source audio language (e.g. en, zh, ja, auto)")
    target_language: str = Field(default="vi", description="Target translated language (e.g. vi)")
    mode: str = Field(default="LIVE_DUB_BILINGUAL", description="Mode: CAPTION_ONLY, CAPTION_TRANSLATE, LIVE_DUB, LIVE_DUB_BILINGUAL")
    voice_profile_id: Optional[str] = Field(default=None, description="Optional Voice Vault profile ID")
    gender_preference: Optional[str] = Field(default="male", description="male or female")
    device_id: Optional[str] = Field(default=None, description="Client device identifier")


class SessionResponse(BaseModel):
    ok: bool
    session_id: str
    stream_token: str
    websocket_url: str
    mode: str
    target_language: str


@router.post("/sessions", response_model=SessionResponse)
async def create_live_translate_session(
    req: CreateSessionRequest,
    request: Request,
    account: dict = Depends(require_account),
) -> SessionResponse:
    """Creates a new real-time translation session requiring authenticated account."""
    owner_id = str(account.get("id") or account.get("account_id") or "").strip()
    if not owner_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="CREATE_OWNER_AUTH: Invalid account identity")

    mode_enum = (
        RealtimeTranslateMode(req.mode)
        if req.mode in RealtimeTranslateMode._value2member_map_
        else RealtimeTranslateMode.LIVE_DUB_BILINGUAL
    )

    # PRICING ADMISSION CHECK (Owner decision unresolved -> fail closed on production)
    if not is_pricing_admission_allowed(mode_enum):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"PRICING_NOT_CONFIGURED: Production paid admission for mode '{mode_enum.value}' is blocked until Owner pricing decision.",
        )

    session_id = f"rts_{uuid.uuid4().hex[:12]}"
    device_id = req.device_id or f"dev_{uuid.uuid4().hex[:8]}"

    config = RealtimeSessionConfig(
        owner_id=owner_id,
        source_language=req.source_language,
        target_language=req.target_language,
        mode=mode_enum,
        voice_profile_id=req.voice_profile_id,
        gender_preference=req.gender_preference or "male",
        client_device_id=device_id,
    )

    session = RealtimeTranslateSession(session_id, config)
    _ACTIVE_SESSIONS[session_id] = session
    _ACTIVE_INGRESS_BUFFERS[session_id] = RealtimeAudioIngressBuffer()

    exp = int(time.time()) + TOKEN_TTL_SECONDS
    try:
        stream_token = generate_stream_token(session_id, owner_id, device_id, exp)
    except RuntimeError as e:
        logger.error(f"Failed to generate stream token (fail closed): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server stream security configuration missing")

    ws_url = f"/api/v1/live-translate/sessions/{session_id}/stream?token={stream_token}"

    return SessionResponse(
        ok=True,
        session_id=session_id,
        stream_token=stream_token,
        websocket_url=ws_url,
        mode=mode_enum.value,
        target_language=req.target_language,
    )


@router.get("/sessions/{session_id}")
async def get_session_status(
    session_id: str,
    account: dict = Depends(require_account),
) -> Dict[str, Any]:
    """Retrieves session metadata, enforcing owner isolation (STATUS_OWNER_AUTH)."""
    owner_id = str(account.get("id") or account.get("account_id") or "").strip()
    session = _ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if str(session.config.owner_id) != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: session belongs to another owner")
    return {"ok": True, **session.to_dict()}


@router.post("/sessions/{session_id}/stop")
async def stop_session(
    session_id: str,
    request: Request = None,
    token: Optional[str] = Query(None),
    account: Optional[dict] = Depends(lambda: None),
) -> Dict[str, Any]:
    """Idempotently stops a session, enforcing owner isolation (STOP_OWNER_AUTH).
    Supports either session cookie account authentication OR stream token authentication.
    """
    owner_id = ""
    if account and isinstance(account, dict):
        owner_id = str(account.get("id") or account.get("account_id") or "").strip()

    if not owner_id and token:
        token_claims = verify_stream_token(token, session_id)
        if token_claims and token_claims[0]:
            owner_id = str(token_claims[0]).strip()

    if not owner_id and request:
        auth_header = request.headers.get("Authorization", "").strip()
        if auth_header.lower().startswith("bearer "):
            bearer = auth_header[7:].strip()
            token_claims = verify_stream_token(bearer, session_id)
            if token_claims and token_claims[0]:
                owner_id = str(token_claims[0]).strip()
        if not owner_id:
            try:
                acc = require_account(request)
                if acc:
                    owner_id = str(acc.get("id") or acc.get("account_id") or "").strip()
            except Exception:
                pass

    if not owner_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: valid session cookie or stream token required",
        )

    session = _ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if str(session.config.owner_id) != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: session belongs to another owner")

    session.end()
    _ACTIVE_INGRESS_BUFFERS.pop(session_id, None)
    return {"ok": True, "session_id": session_id, "state": session.state.value}


@router.get("/sessions/{session_id}/export")
async def export_session_subtitles(
    session_id: str,
    format: str = Query("srt", pattern="^(srt|vtt)$"),
    account: dict = Depends(require_account),
) -> Dict[str, Any]:
    """Exports transcript as SRT or WebVTT subtitles, enforcing owner scope (EXPORT_OWNER_AUTH)."""
    owner_id = str(account.get("id") or account.get("account_id") or "").strip()
    session = _ACTIVE_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if str(session.config.owner_id) != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: session belongs to another owner")

    content = session.export_srt(owner_id) if format == "srt" else session.export_vtt(owner_id)
    return {"ok": True, "format": format, "content": content}


class BotBridgeResponse(list):
    """Encapsulates canonical Bot bridge events and execution outcome.

    Inherits from list for backward-compatibility with code iterating directly over safe events.
    Exposes status ('success', 'permanent_rejection', 'transient_failure'), error_code, and error_detail.
    """
    def __init__(
        self,
        events: Optional[List[Dict[str, Any]]] = None,
        status: str = "success",
        error_code: str = "",
        error_detail: str = "",
        status_code: int = 200,
    ):
        super().__init__(events or [])
        self.status = status  # 'success' | 'permanent_rejection' | 'transient_failure'
        self.error_code = error_code
        self.error_detail = error_detail
        self.status_code = status_code
        self.ok = (status == "success")


async def forward_segment_to_bot(
    session: RealtimeTranslateSession,
    sequence: int,
    speech_seg: SpeechSegment,
) -> BotBridgeResponse:
    """Signs and forwards audio segment to Bot canonical internal realtime route via actual Core Bridge."""

    payload = {
        "session_id": session.session_id,
        "actor_id": str(session.config.owner_id),
        "sequence": sequence,
        "segment_id": speech_seg.segment_id,
        "pcm_bytes_b64": base64.b64encode(speech_seg.pcm_bytes).decode("ascii"),
        "start_ms": speech_seg.start_ms,
        "end_ms": speech_seg.end_ms,
        "source_language": session.config.source_language,
        "target_language": session.config.target_language,
        "mode": session.config.mode.value,
        "voice_profile_id": session.config.voice_profile_id,
        "gender_preference": session.config.gender_preference,
    }

    try:
        from copyfast_bridge import bridge_request
        bridge_res = await bridge_request(
            "POST",
            "/internal/v1/realtime/process-chunk",
            payload=payload,
            actor_id=str(session.config.owner_id),
        )
        if isinstance(bridge_res, dict):
            events = bridge_res.get("events")
            if events is None and isinstance(bridge_res.get("data"), dict):
                events = bridge_res["data"].get("events")

            if bridge_res.get("ok", True) and events is not None:
                return BotBridgeResponse(
                    events=events if isinstance(events, list) else [],
                    status="success",
                    status_code=200,
                )

            err_code = str(bridge_res.get("error_code") or "")
            err_msg = str(bridge_res.get("message") or "")
            status_name = str(bridge_res.get("status") or "")

            is_permanent = (
                err_code in {
                    "CORE_BRIDGE_FORBIDDEN",
                    "CORE_BRIDGE_UNAUTHORIZED",
                    "CORE_BRIDGE_UNPROCESSABLE",
                    "CORE_BRIDGE_BAD_REQUEST",
                    "FOREIGN_PROFILE_BLOCKED",
                    "DELETED_PROFILE_BLOCKED",
                    "NOT_READY_PROFILE_BLOCKED",
                    "MISSING_PROFILE_BLOCKED",
                    "MISSING_PROVIDER_VOICE_ID",
                    "VOICE_VALIDATION_FAILED",
                    "ACTOR_BODY_HEADER_MISMATCH",
                }
                or "PROFILE" in err_code
                or "VOICE" in err_code
                or "AUTH" in err_code
                or "ACTOR" in err_code
                or "SIGNATURE" in err_code
            )

            if is_permanent:
                return BotBridgeResponse(
                    events=[],
                    status="permanent_rejection",
                    error_code=err_code or "PERMANENT_REJECTION",
                    error_detail=err_msg or status_name,
                    status_code=422 if "PROFILE" in err_code or "VOICE" in err_code else 400,
                )
            else:
                return BotBridgeResponse(
                    events=[],
                    status="transient_failure",
                    error_code=err_code or "CORE_BRIDGE_UNAVAILABLE",
                    error_detail=err_msg or status_name,
                    status_code=503,
                )
    except Exception as e:
        logger.error(f"Core bridge call to Bot realtime failed: {e}")
        return BotBridgeResponse(
            events=[],
            status="transient_failure",
            error_code="CORE_BRIDGE_UNAVAILABLE",
            error_detail=str(e),
            status_code=503,
        )

    return BotBridgeResponse(
        events=[],
        status="transient_failure",
        error_code="CORE_BRIDGE_INVALID_RESPONSE",
        status_code=500,
    )


@router.websocket("/sessions/{session_id}/stream")
async def websocket_live_stream(websocket: WebSocket, session_id: str, token: str = Query(...)):
    """WebSocket bidirectional live streaming route for audio and subtitles.

    Enforces:
    1. WS_OWNER_AUTH: Valid stream token signature and expiration.
    2. TOKEN_OWNER_ID == SESSION_OWNER_ID verification.
    3. Monotonic sequence deduplication and server ACK.
    4. Client reconnect handling.
    """
    token_res = verify_stream_token(token, session_id)
    if not token_res:
        await websocket.close(code=4401, reason="Unauthorized or invalid stream token")
        return
    token_owner_id, token_device_id = token_res

    session = _ACTIVE_SESSIONS.get(session_id)
    ingress = _ACTIVE_INGRESS_BUFFERS.get(session_id)
    if not session or not ingress:
        await websocket.close(code=4404, reason="Session not found")
        return

    # Verify TOKEN_OWNER_ID == SESSION_OWNER_ID
    if str(token_owner_id) != str(session.config.owner_id):
        await websocket.close(code=4403, reason="Forbidden: token owner mismatch")
        return

    await websocket.accept()
    socket_lease: int = session.acquire_socket_lease(websocket)
    if session.state == RealtimeSessionState.CREATED:
        session.start()
    elif session.state == RealtimeSessionState.PAUSED:
        session.resume()

    explicitly_ended: bool = False

    try:
        await websocket.send_json({
            "type": "session.ready",
            "session_id": session_id,
            "mode": session.config.mode.value,
            "target_language": session.config.target_language,
            "last_ack_seq": session.last_ack_seq,
        })

        while True:
            if not session.is_socket_lease_active(socket_lease):
                logger.info(
                    f"Session {session_id} socket lease {socket_lease} superseded by active lease {session.current_socket_lease}. Closing stale socket."
                )
                await websocket.close(code=4409, reason="Socket lease superseded by newer connection")
                break

            message = await websocket.receive()

            # CRITICAL (RT-FIX11): LEASE_RECHECK_AFTER_RECEIVE
            # Re-check lease immediately after unblocking from receive()
            if not session.is_socket_lease_active(socket_lease):
                logger.info(
                    f"Session {session_id} socket lease {socket_lease} superseded during receive. "
                    f"Active lease: {session.current_socket_lease}. Dropping message and closing stale socket."
                )
                await websocket.close(code=4409, reason="Socket lease superseded during receive")
                break

            if "bytes" in message and message["bytes"]:
                if not session.is_socket_lease_active(socket_lease):
                    await websocket.close(code=4409, reason="Socket lease superseded")
                    break
                raw = message["bytes"]
                if len(raw) < 4:
                    continue

                seq = struct.unpack("<I", raw[:4])[0]
                pcm_bytes = raw[4:]
                chunk_dur_ms = int((len(pcm_bytes) / 32000) * 1000)

                if not session.accept_audio_sequence(seq, duration_ms=chunk_dur_ms):
                    await websocket.send_json({"type": "ack", "seq": seq, "status": "duplicate_ignored"})
                    continue

                if seq in session.pending_retry_segments:
                    # Retry of pending segment covering range: reuse stored SpeechSegment directly;
                    # DO NOT re-ingest PCM into ingress buffer (PENDING_RANGE_PCM_REINGEST_COUNT=0)!
                    completed_segments = [session.pending_retry_segments[seq]]
                elif seq in session.buffered_seq_set:
                    # Frame already buffered in ingress awaiting VAD segment boundary: ignore duplicate PCM!
                    await websocket.send_json({"type": "buffered", "seq": seq})
                    continue
                else:
                    completed_segments = ingress.push_chunk(seq=seq, pcm_bytes=pcm_bytes)

                if completed_segments:
                    for speech_seg in completed_segments:
                        if not session.is_socket_lease_active(socket_lease):
                            logger.info(f"Socket lease {socket_lease} superseded before Bot bridge call. Aborting.")
                            break

                        # Concurrency guard: exactly-one bridge execution per segment across concurrent sockets
                        if speech_seg.segment_id in session.in_flight_segments:
                            logger.info(f"Segment {speech_seg.segment_id} already in-flight to Bot bridge. Skipping concurrent duplicate.")
                            continue

                        session.in_flight_segments.add(speech_seg.segment_id)
                        try:
                            # Forward to Bot internal realtime bridge
                            bridge_res = await forward_segment_to_bot(session, speech_seg.sequence_end, speech_seg)
                        finally:
                            session.in_flight_segments.discard(speech_seg.segment_id)

                        if not session.is_socket_lease_active(socket_lease):
                            logger.info(f"Socket lease {socket_lease} superseded during Bot bridge call. Aborting.")
                            break
                        if bridge_res.status == "success":
                            stt_text = ""
                            trans_text = ""
                            tts_b64 = None
                            for ev in bridge_res:
                                ev_type = ev.get("type")
                                if ev_type == "stt.final":
                                    stt_text = ev.get("source_text", "")
                                elif ev_type == "translation.final":
                                    trans_text = ev.get("translated_text", "")
                                elif ev_type == "tts.audio":
                                    tts_b64 = ev.get("audio_b64")
                                # Safe event relay: send real bot-shaped event directly to client WS
                                await websocket.send_json(ev)

                            if stt_text:
                                transcript_seg = RealtimeTranscriptSegment(
                                    segment_id=speech_seg.segment_id,
                                    sequence=speech_seg.sequence_end,
                                    start_ms=speech_seg.start_ms,
                                    end_ms=speech_seg.end_ms,
                                    source_text=stt_text,
                                    translated_text=trans_text,
                                    is_final=True,
                                    tts_audio_base64=tts_b64,
                                )
                                session.add_segment(transcript_seg)

                            # BOT_PROCESS_SUCCESS -> mark_range_processed -> cumulative ACK closing whole range
                            ack_seq = session.mark_range_processed(speech_seg.sequence_start, speech_seg.sequence_end)
                            await websocket.send_json({"type": "ack", "seq": ack_seq})

                            new_blocks = session.compute_pending_metering_blocks()
                            if new_blocks > 0:
                                await websocket.send_json(session.get_telemetry_usage())

                        elif bridge_res.status == "permanent_rejection":
                            # BOT_PERMANENT_REJECTION -> safe error event -> mark entire range rejected
                            session.mark_range_rejected(speech_seg.sequence_start, speech_seg.sequence_end)
                            safe_err_event = {
                                "type": "error",
                                "error_code": bridge_res.error_code or "PERMANENT_REJECTION",
                                "message": "Speech processing rejected by server authority.",
                                "sequence": speech_seg.sequence_end,
                                "sequence_start": speech_seg.sequence_start,
                                "sequence_end": speech_seg.sequence_end,
                                "segment_id": speech_seg.segment_id,
                                "fatal": False,
                            }
                            await websocket.send_json(safe_err_event)
                            # NO mark_range_processed
                            # NO success ACK

                        else:
                            # BOT_TIMEOUT/5XX/NETWORK/MALFORMED -> NO mark processed -> NO success ACK -> preserve segment across full range
                            session.add_pending_retry_segment(speech_seg)
                            logger.warning(
                                "Transient Bot bridge failure for seq range [%s..%s] session=%s: %s",
                                speech_seg.sequence_start, speech_seg.sequence_end, session_id, bridge_res.error_code
                            )
                            # NO mark_range_processed
                            # NO success ACK
                else:
                    # Ingress buffer accepted chunk; segment boundary not yet reached.
                    # CRITICAL (Section A): Do NOT mark processed as Bot success!
                    session.mark_sequence_buffered(seq)
                    await websocket.send_json({"type": "buffered", "seq": seq})

            elif "text" in message and message["text"]:
                try:
                    ctrl = json.loads(message["text"])
                    msg_type = ctrl.get("type", "")
                    if msg_type == "session.reconnect":
                        client_last_ack = int(ctrl.get("last_ack_seq", 0))
                        recon_info = session.handle_reconnect(client_last_ack)
                        ingress.clear_partial()
                        await websocket.send_json({"type": "session.reconnected", **recon_info})
                    elif msg_type == "session.control":
                        action = ctrl.get("action", "").lower()
                        if action == "pause":
                            session.pause()
                            await websocket.send_json({"type": "session.state", "state": "paused"})
                        elif action == "resume":
                            session.resume()
                            await websocket.send_json({"type": "session.state", "state": "active"})
                        elif action == "stop":
                            explicitly_ended = True
                            session.end()
                            _ACTIVE_INGRESS_BUFFERS.pop(session_id, None)
                            await websocket.send_json({"type": "session.state", "state": "ended"})
                            break
                except Exception as e:
                    logger.warning(f"Error handling control message: {e}")

    except WebSocketDisconnect:
        logger.info(f"Session {session_id} WebSocket disconnected.")
    except Exception as e:
        logger.error(f"Session {session_id} unexpected error: {e}")
        session.fail(str(e))
    finally:
        if explicitly_ended or session.state in (RealtimeSessionState.ENDED, RealtimeSessionState.ERROR):
            session.end()
            _ACTIVE_INGRESS_BUFFERS.pop(session_id, None)
        else:
            if session.is_socket_lease_active(socket_lease):
                logger.info(
                    f"Session {session_id} WebSocket detached (reconnectable). Preserving state ({session.state.value}) and ingress buffer."
                )
            else:
                logger.info(
                    f"Session {session_id} stale socket lease {socket_lease} detached. Active lease {session.current_socket_lease} retained."
                )
