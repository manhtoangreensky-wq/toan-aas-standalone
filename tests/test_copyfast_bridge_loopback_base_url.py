import pytest

from copyfast_bridge import _valid_base_url


@pytest.mark.parametrize(
    "value",
    [
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://[::1]:8080",
    ],
)
def test_core_bridge_allows_explicit_loopback_http_origins(value: str) -> None:
    assert _valid_base_url(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "http://toanaas.vn",
        "http://example.com",
        "http://192.168.1.10:8080",
        "http://10.0.0.1:8080",
        "http://172.16.0.1:8080",
        "http://0.0.0.0:8080",
    ],
)
def test_core_bridge_rejects_non_loopback_plain_http(value: str) -> None:
    assert _valid_base_url(value) is False


@pytest.mark.parametrize(
    "value",
    [
        "http://user:password@127.0.0.1:8080",
        "http://127.0.0.1:8080/internal/v1/admin/wallet/credit",
        "http://127.0.0.1:8080?debug=1",
        "http://127.0.0.1:8080#fragment",
        "http://127.0.0.1:not-a-port",
    ],
)
def test_core_bridge_loopback_http_still_requires_root_origin_shape(value: str) -> None:
    assert _valid_base_url(value) is False


def test_core_bridge_preserves_existing_https_origin_behavior() -> None:
    assert _valid_base_url("https://toanaas.vn") is True
    assert _valid_base_url("https://example.com:443/") is True
    assert _valid_base_url("https://127.0.0.1:8080") is True
