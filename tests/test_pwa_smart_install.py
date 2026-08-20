from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_pwa_manifest_endpoint():
    response = client.get("/manifest.json")
    assert response.status_code == 200
    assert "json" in response.headers.get("content-type", "")
    data = response.json()
    assert data["name"] == "TOAN AAS - Autonomous Automation Suite"
    assert data["short_name"] == "TOAN AAS"
    assert data["display"] == "standalone"
    assert data["start_url"] == "/portal"
    assert len(data["icons"]) >= 4
    assert any(icon["sizes"] == "192x192" for icon in data["icons"])
    assert any(icon["sizes"] == "512x512" for icon in data["icons"])
    assert any("maskable" in icon.get("purpose", "") for icon in data["icons"])
    assert len(data.get("shortcuts", [])) >= 2

def test_pwa_manifest_webmanifest_alias():
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert "json" in response.headers.get("content-type", "")

def test_pwa_service_worker_endpoint():
    response = client.get("/service-worker.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")
    assert "CACHE_NAME" in response.text
    assert "addEventListener" in response.text
    assert "skipWaiting" in response.text

def test_pwa_service_worker_alias():
    response = client.get("/portal-sw.js")
    assert response.status_code == 200
    assert "javascript" in response.headers.get("content-type", "")

def test_pwa_offline_fallback_endpoint():
    response = client.get("/offline.html")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Offline Mode" in response.text or "Ngoại tuyến" in response.text
    assert "TOAN AAS" in response.text

def test_pwa_meta_in_portal_pages():
    response = client.get("/login")
    assert response.status_code == 200
    html = response.text
    assert 'rel="manifest" href="/manifest.json"' in html
    assert 'name="theme-color"' in html
    assert 'name="apple-mobile-web-app-capable" content="yes"' in html
    assert 'rel="apple-touch-icon"' in html
    assert 'portal-theme.js' in html
    assert 'portal.js' in html
