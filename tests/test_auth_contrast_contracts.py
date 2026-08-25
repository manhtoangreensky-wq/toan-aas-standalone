import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "static" / "portal" / "portal.css").read_text(encoding="utf-8")


def _declarations(selector: str) -> dict[str, str]:
    match = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", CSS)
    assert match, f"Missing CSS block: {selector}"
    return {
        name.strip(): value.strip()
        for name, value in re.findall(r"([\w-]+)\s*:\s*([^;]+);", match.group(1))
    }


def _channel(value: int) -> float:
    normalized = value / 255
    return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    red, green, blue = (int(hex_color[index:index + 2], 16) for index in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_colored_telegram_button_uses_white_text_with_readable_contrast() -> None:
    telegram = _declarations(".portal-btn-direct-social.telegram")

    assert re.fullmatch(r"#[0-9a-fA-F]{6}", telegram["background"])
    assert telegram["color"].lower() == "#ffffff"
    assert _contrast(telegram["background"], telegram["color"]) >= 4.5


def test_light_auth_buttons_keep_the_inverse_surface_rule() -> None:
    google = _declarations('[data-portal-theme="light"] .portal-btn-direct-social.google')
    apple = _declarations('[data-portal-theme="light"] .portal-btn-direct-social.apple')

    assert google["background"].lower() == "#ffffff"
    assert _contrast(google["background"], google["color"]) >= 4.5
    assert apple["color"].lower() == "#ffffff"
    assert _contrast(apple["background"], apple["color"]) >= 4.5
