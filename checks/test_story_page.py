"""Page test for "Play the story": it advances only on a click of Next, one step per click. Starts its own public-mode
server on a free port; skipped when Playwright or a Chromium-family browser is not available."""
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
pw = pytest.importorskip("playwright.sync_api")


@pytest.fixture(scope="module")
def url():
    with socket.socket() as so:
        so.bind(("127.0.0.1", 0))
        port = so.getsockname()[1]
    env = dict(os.environ, SNS_PUBLIC="1", SNS_DB=str(Path(tempfile.mkdtemp()) / "t.db"), SNS_MODEL="/nonexistent")
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.server:app", "--port", str(port)], cwd=ROOT, env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    u = f"http://127.0.0.1:{port}"
    for _ in range(240):
        try:
            urllib.request.urlopen(u + "/config", timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.kill()
        pytest.skip("server did not start")
    yield u
    proc.kill()


def step_no(page):
    m = re.match(r"(\d)/6", page.inner_text("#storycap"))
    return int(m.group(1)) if m else 0


def test_story_advances_only_on_next(url):
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="msedge")
        except Exception:
            try:
                b = p.chromium.launch()
            except Exception:
                pytest.skip("no Chromium-family browser")
        pg = b.new_page(viewport={"width": 1366, "height": 768})
        pg.goto(url + "/")
        pg.wait_for_selector("#play")
        time.sleep(1.5)
        pg.click("#play")
        pg.wait_for_function("!document.getElementById('story').hidden")
        pg.click("#storynext")                                   # -> step 1
        pg.wait_for_function("!document.getElementById('storynext').disabled", timeout=20000)
        assert step_no(pg) == 1
        time.sleep(20)                                           # no click: must stay on step 1
        assert step_no(pg) == 1
        pg.click("#storynext")                                   # one click -> exactly step 2
        pg.wait_for_function("!document.getElementById('storynext').disabled", timeout=20000)
        assert step_no(pg) == 2
        pg.dblclick("#storynext", force=True)                    # double click -> one step forward only
        pg.wait_for_function("!document.getElementById('storynext').disabled", timeout=20000)
        time.sleep(1)
        assert step_no(pg) == 3
        b.close()
