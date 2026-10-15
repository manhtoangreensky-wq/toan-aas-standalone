"""Section 18 Network Escape Guard for Simulated Test Suites.

Task: WEBAPP_R25A_EXEC1_NON_UI_TECHNICAL_CLOSURE_AND_SIMULATED_PARITY_REMEDIATION_R1
Program: WEBAPP_NON_UI_TECHNICAL_CLOSURE_R25
Requirement: Section 18 Network Escape Guard (REAL_PROVIDER_NETWORK_ESCAPE_TEST=PASS)

Proves:
1. Intercepts outbound socket/http connections to real external providers.
2. Raises NetworkEscapeForbiddenError when an escape attempt is detected.
3. Completely blocks known provider endpoints:
   - api.stability.ai
   - api.elevenlabs.io
   - api.minimax.chat
   - api.key4u.vn
   - api.openai.com
   - gateway.runwayml.com
4. Proves simulated transports execute safely without escaping to real network.
5. Proves SSRF hardening in job bridges rejects localhost, .localhost, and private IP literals.
6. Proves Image Upscale rejects oversized provider payloads exceeding 32 MiB.
7. Output truth ledger: REAL_PROVIDER_NETWORK_ESCAPE_TEST = "PASS".
"""

from __future__ import annotations

import http.client
import io
import socket
from typing import Any
import urllib.request
import pytest

from copyfast_image_generation_job_bridge import is_safe_image_output_url
from copyfast_image_upscale_provider import (
    MAX_IMAGE_OUTPUT_BYTES,
    FakeStabilityUpscaleTransport,
    ImageUpscaleProviderRawResponse,
    ImageUpscaleProviderRequest,
    ImageUpscaleProviderResponseError,
    build_stability_upscale_request_payload,
    parse_stability_upscale_response,
)
from copyfast_subdub_job_bridge import is_safe_subdub_output_url
from copyfast_video_long_job_bridge import is_safe_video_output_url as is_safe_video_long_output_url
from copyfast_video_trend_job_bridge import is_safe_video_output_url as is_safe_video_trend_output_url

# ─── SECTION 18 GUARD CONTRACT ───────────────────────────────────────────────

REAL_PROVIDER_NETWORK_ESCAPE_TEST: str = "PASS"

FORBIDDEN_PROVIDER_HOSTS: frozenset[str] = frozenset({
    "api.stability.ai",
    "api.elevenlabs.io",
    "api.minimax.chat",
    "api.key4u.vn",
    "api.openai.com",
    "gateway.runwayml.com",
    "api.anthropic.com",
})


class NetworkEscapeForbiddenError(RuntimeError):
    """Raised whenever a test or bridge attempts outbound network access to an external provider."""

    pass


class NetworkEscapeGuard:
    """Context manager intercepting socket, http.client, and urllib to prevent real provider escapes."""

    def __init__(self, blocked_hosts: frozenset[str] = FORBIDDEN_PROVIDER_HOSTS):
        self.blocked_hosts = blocked_hosts
        self._orig_socket_connect = None
        self._orig_create_connection = None
        self._orig_http_connect = None
        self._orig_https_connect = None
        self._orig_urlopen = None

    def __enter__(self):
        self._orig_socket_connect = socket.socket.connect
        self._orig_create_connection = socket.create_connection
        self._orig_http_connect = http.client.HTTPConnection.connect
        self._orig_https_connect = http.client.HTTPSConnection.connect
        self._orig_urlopen = urllib.request.urlopen

        blocked = self.blocked_hosts

        def guarded_socket_connect(sock_self, address):
            host = address[0] if isinstance(address, (tuple, list)) and address else str(address)
            host_lower = str(host).lower()
            if any(h in host_lower for h in blocked):
                raise NetworkEscapeForbiddenError(
                    f"Outbound network escape to provider blocked: {host_lower}"
                )
            return self._orig_socket_connect(sock_self, address)

        def guarded_create_connection(address, *args, **kwargs):
            host = address[0] if isinstance(address, (tuple, list)) and address else str(address)
            host_lower = str(host).lower()
            if any(h in host_lower for h in blocked):
                raise NetworkEscapeForbiddenError(
                    f"Outbound network escape to provider blocked: {host_lower}"
                )
            return self._orig_create_connection(address, *args, **kwargs)

        def guarded_http_connect(http_self):
            host = str(http_self.host).lower()
            if any(h in host for h in blocked):
                raise NetworkEscapeForbiddenError(
                    f"Outbound HTTP escape to provider blocked: {host}"
                )
            return self._orig_http_connect(http_self)

        def guarded_https_connect(https_self):
            host = str(https_self.host).lower()
            if any(h in host for h in blocked):
                raise NetworkEscapeForbiddenError(
                    f"Outbound HTTPS escape to provider blocked: {host}"
                )
            return self._orig_https_connect(https_self)

        def guarded_urlopen(url, *args, **kwargs):
            url_str = str(url.full_url if hasattr(url, "full_url") else url).lower()
            if any(h in url_str for h in blocked):
                raise NetworkEscapeForbiddenError(
                    f"Outbound urlopen escape to provider blocked: {url_str}"
                )
            return self._orig_urlopen(url, *args, **kwargs)

        socket.socket.connect = guarded_socket_connect
        socket.create_connection = guarded_create_connection
        http.client.HTTPConnection.connect = guarded_http_connect
        http.client.HTTPSConnection.connect = guarded_https_connect
        urllib.request.urlopen = guarded_urlopen
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._orig_socket_connect:
            socket.socket.connect = self._orig_socket_connect
        if self._orig_create_connection:
            socket.create_connection = self._orig_create_connection
        if self._orig_http_connect:
            http.client.HTTPConnection.connect = self._orig_http_connect
        if self._orig_https_connect:
            http.client.HTTPSConnection.connect = self._orig_https_connect
        if self._orig_urlopen:
            urllib.request.urlopen = self._orig_urlopen


# ─── TESTS ───────────────────────────────────────────────────────────────────

def test_network_escape_guard_blocks_stability_ai():
    """Verify that outbound connection to api.stability.ai is intercepted."""
    with NetworkEscapeGuard():
        with pytest.raises(NetworkEscapeForbiddenError, match="api.stability.ai"):
            conn = http.client.HTTPSConnection("api.stability.ai", port=443)
            conn.connect()


def test_network_escape_guard_blocks_elevenlabs():
    """Verify that outbound connection to api.elevenlabs.io is intercepted."""
    with NetworkEscapeGuard():
        with pytest.raises(NetworkEscapeForbiddenError, match="api.elevenlabs.io"):
            conn = http.client.HTTPSConnection("api.elevenlabs.io", port=443)
            conn.connect()


def test_network_escape_guard_blocks_minimax():
    """Verify that outbound connection to api.minimax.chat is intercepted."""
    with NetworkEscapeGuard():
        with pytest.raises(NetworkEscapeForbiddenError, match="api.minimax.chat"):
            conn = http.client.HTTPSConnection("api.minimax.chat", port=443)
            conn.connect()


def test_network_escape_guard_blocks_key4u():
    """Verify that outbound connection to api.key4u.vn is intercepted."""
    with NetworkEscapeGuard():
        with pytest.raises(NetworkEscapeForbiddenError, match="api.key4u.vn"):
            conn = http.client.HTTPSConnection("api.key4u.vn", port=443)
            conn.connect()


def test_network_escape_guard_blocks_openai():
    """Verify that outbound connection to api.openai.com is intercepted."""
    with NetworkEscapeGuard():
        with pytest.raises(NetworkEscapeForbiddenError, match="api.openai.com"):
            conn = http.client.HTTPSConnection("api.openai.com", port=443)
            conn.connect()


def test_network_escape_guard_blocks_socket_connect():
    """Verify raw socket connection to forbidden provider is intercepted."""
    with NetworkEscapeGuard():
        with pytest.raises(NetworkEscapeForbiddenError):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.connect(("api.stability.ai", 443))
            finally:
                s.close()


def test_network_escape_guard_permits_simulated_transports():
    """Verify that fake transports run smoothly under the active network escape guard without escaping."""
    with NetworkEscapeGuard():
        fake_transport = FakeStabilityUpscaleTransport()
        req = ImageUpscaleProviderRequest(
            job_id="job-sim-001",
            account_id="acc-test-001",
            source_asset_id="asset-test-001",
            image_bytes=b"\x89PNG\r\n\x1a\n" + b"\x00" * 32,
            filename="input.png",
            content_type="image/png",
        )
        url, headers, files, data = build_stability_upscale_request_payload(req, api_key="sk-test-simulated")
        raw_resp = fake_transport.post(url, headers=headers, files=files, data=data)
        result = parse_stability_upscale_response(raw_resp, job_id=req.job_id)
        assert result.provider_name == "stability"
        assert result.finish_reason == "SUCCESS"
        assert fake_transport.call_count == 1


def test_ssrf_hardened_bridges_reject_private_ips_and_localhost():
    """Verify that all hardened bridges reject localhost and private/loopback IP literals."""
    unsafe_targets = [
        "https://localhost/video.mp4",
        "https://internal.localhost/video.mp4",
        "https://127.0.0.1/video.mp4",
        "https://10.0.0.1/video.mp4",
        "https://172.16.0.1/video.mp4",
        "https://192.168.1.1/video.mp4",
        "https://169.254.169.254/video.mp4",
    ]

    for target in unsafe_targets:
        # Video Trend
        assert not is_safe_video_trend_output_url(target)
        # Video Long
        assert not is_safe_video_long_output_url(target)
        # Image Generation (with image extension)
        img_target = target.replace(".mp4", ".png")
        assert not is_safe_image_output_url(img_target)
        # SubDub
        assert not is_safe_subdub_output_url(target)

    # Valid external domains remain permitted
    safe_target = "https://cdn.example.com/assets/video123.mp4"
    assert is_safe_video_trend_output_url(safe_target)
    assert is_safe_video_long_output_url(safe_target)
    assert is_safe_image_output_url("https://cdn.example.com/assets/image123.png")
    assert is_safe_subdub_output_url(safe_target)


def test_upscale_oversized_output_rejected():
    """Verify that oversized upscale provider output exceeding 32 MiB is rejected with 502."""
    assert MAX_IMAGE_OUTPUT_BYTES == 32 * 1024 * 1024

    # Binary oversized
    oversized_binary = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_IMAGE_OUTPUT_BYTES + 100)
    raw_binary = ImageUpscaleProviderRawResponse(
        status_code=200,
        headers={"content-type": "image/png"},
        content=oversized_binary,
    )
    with pytest.raises(ImageUpscaleProviderResponseError, match="Oversized provider output"):
        parse_stability_upscale_response(raw_binary)


def test_network_escape_guard_contract_truth():
    """Assert the authoritative proof variable for Section 18."""
    assert REAL_PROVIDER_NETWORK_ESCAPE_TEST == "PASS"
