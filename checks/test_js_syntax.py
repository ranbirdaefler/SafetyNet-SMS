"""node --check on every served .js file and every inline <script> in served pages (a JS syntax error stops the
whole page script; e712cf6 shipped one). Skipped when node is not installed (e.g. on the Pi)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
PAGES = sorted((ROOT / "sim").glob("*.html"))
SCRIPTS = sorted(p for p in (ROOT / "sim").rglob("*.js") if "ort" not in p.name)   # vendored onnxruntime-web excluded


def check(src, tmp_path, name):
    f = tmp_path / name
    f.write_text(src, encoding="utf-8")
    r = subprocess.run([NODE, "--check", str(f)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("page", PAGES, ids=lambda p: p.name)
def test_inline_scripts(page, tmp_path):
    html = page.read_text(encoding="utf-8")
    blocks = re.findall(r"<script([^>]*)>(.*?)</script>", html, re.S)
    for i, (attrs, body) in enumerate(blocks):
        if "src=" in attrs or not body.strip():
            continue
        check(body, tmp_path, f"{page.stem}_{i}.mjs" if "module" in attrs else f"{page.stem}_{i}.js")


@pytest.mark.skipif(NODE is None, reason="node not installed")
@pytest.mark.parametrize("js", SCRIPTS, ids=lambda p: p.name)
def test_js_files(js, tmp_path):
    check(js.read_text(encoding="utf-8"), tmp_path, js.name if js.suffix == ".mjs" else js.stem + ".mjs")
