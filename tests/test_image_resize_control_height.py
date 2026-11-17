"""Real Chrome geometry over the current rendered form/CSS; no app, DB or product API."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import websockets

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.ci.run_browser_verification import find_chrome_executable, launch_headless_chrome


async def _samples(directory: Path) -> dict:
    node = shutil.which("node")
    assert node, "Existing Node runtime is required"
    rendered = json.loads(subprocess.check_output(
        [node, str(ROOT / "tests/helpers/image-resize-layout-html.mjs")],
        cwd=ROOT, text=True, encoding="utf8", timeout=20))
    css = "\n".join((ROOT / file).read_text(encoding="utf8")
                    for file in ("static/portal/portal.css", "static/portal/portal-theme.css"))
    chrome = launch_headless_chrome(find_chrome_executable(), directory, max_attempts=1)
    rows = {}
    try:
        async with websockets.connect(chrome.ws_url, max_size=8 * 1024 * 1024) as ws:
            call_id = 0
            session_id = None

            async def send(method, params=None, page=False):
                nonlocal call_id
                call_id += 1
                current = call_id
                message = {"id": current, "method": method, "params": params or {}}
                if page:
                    message["sessionId"] = session_id
                await ws.send(json.dumps(message))
                while True:
                    response = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
                    if response.get("id") == current:
                        assert "error" not in response, response.get("error")
                        return response.get("result", {})

            target = await send("Target.createTarget", {"url": "about:blank"})
            attached = await send("Target.attachToTarget", {"targetId": target["targetId"], "flatten": True})
            session_id = attached["sessionId"]
            for domain in ("Page", "Runtime", "Network"):
                await send(domain + ".enable", page=True)
            await send("Network.setBlockedURLs", {"urls": ["*"]}, page=True)
            await send("Network.setCacheDisabled", {"cacheDisabled": True}, page=True)

            async def evaluate(expression):
                value = await send("Runtime.evaluate", {
                    "expression": expression, "returnByValue": True, "awaitPromise": True,
                }, page=True)
                assert "exceptionDetails" not in value, value.get("exceptionDetails")
                return value["result"].get("value")

            for locale in ("vi", "en", "zh"):
                for width in (375, 1440):
                    for theme in ("light", "dark"):
                        await send("Emulation.setDeviceMetricsOverride", {
                            "width": width, "height": 950, "deviceScaleFactor": 1, "mobile": width == 375,
                        }, page=True)
                        content_width = 343 if width == 375 else 1088
                        document = (
                            '<!doctype html><html lang="' + locale + '" data-portal-theme="' + theme
                            + '"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                            + "<style>" + css + '</style></head><body><main style="width:'
                            + str(content_width) + 'px;margin:0 auto">' + rendered[locale] + "</main></body></html>"
                        )
                        await evaluate("document.open();document.write(" + json.dumps(document) + ");document.close();")
                        sample = await evaluate("""(async()=>{
                          await document.fonts.ready;
                          await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                          const form=document.querySelector('form[data-portal-action="image-operation-resize"]');
                          const fields=[...form.querySelectorAll(':scope > .portal-fields > .portal-field')];
                          return {viewport:innerWidth,theme:document.documentElement.dataset.portalTheme,
                            overflow:document.documentElement.scrollWidth>innerWidth+1,
                            fields:fields.map(field=>{
                              const control=field.querySelector('input:not([name=asset_reference_q]),select,textarea');
                              const box=control.getBoundingClientRect();
                              return {name:control.name,height:box.height,width:box.width,required:control.required,
                                min:control.min,max:control.max,step:control.step,disabled:control.disabled,
                                options:control.options?[...control.options].map(option=>option.value):null};
                            })};
                        })()""")
                        rows[(locale, width, theme)] = sample
    finally:
        chrome.proc.terminate()
        try:
            chrome.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chrome.proc.kill()
            chrome.proc.wait(timeout=5)
    return rows


@pytest.fixture(scope="module")
def layout_samples(tmp_path_factory):
    return asyncio.run(_samples(tmp_path_factory.mktemp("resize_control_geometry")))


@pytest.mark.parametrize("locale", ("vi", "en", "zh"))
@pytest.mark.parametrize("width", (375, 1440))
@pytest.mark.parametrize("theme", ("light", "dark"))
def test_resize_controls_keep_natural_height_beside_tall_source_picker(layout_samples, locale, width, theme):
    sample = layout_samples[(locale, width, theme)]
    assert sample["viewport"] == width
    assert sample["theme"] == theme
    assert sample["overflow"] is False
    fields = {field["name"]: field for field in sample["fields"]}
    assert list(fields) == ["source_asset_id", "preset", "target_width", "target_height", "fit_mode"]
    for name, field in fields.items():
        assert 44 <= field["height"] <= 48, (locale, width, theme, name, field["height"])
        assert field["disabled"] is False
        assert field["width"] > 0
    assert abs(fields["source_asset_id"]["width"] - fields["preset"]["width"]) < 1
    assert fields["source_asset_id"]["required"] is True
    for name in ("target_width", "target_height"):
        assert fields[name]["required"] is True
        assert (fields[name]["min"], fields[name]["max"], fields[name]["step"]) == ("128", "4096", "1")
    assert fields["preset"]["options"] == ["custom", "1:1", "4:5", "9:16", "16:9", "3:4", "4:3", "3:2", "2:3", "21:9"]
    assert fields["fit_mode"]["options"] == ["pad", "crop", "blur"]
