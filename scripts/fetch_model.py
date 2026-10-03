"""Download the shipped board model from the public Hugging Face model repo and verify SHA-256 before serving.
The expected hashes are committed in config/model_release.json; a mismatch stops the app."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rel = json.loads((ROOT / "config" / "model_release.json").read_text())
cfg = json.loads((ROOT / rel["board_config"]).read_text())
dest = ROOT / cfg["model_dir"]
dest.mkdir(parents=True, exist_ok=True)
for name, sha in rel["sha256"].items():
    p = dest / name
    if not (p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == sha):
        urllib.request.urlretrieve(f"https://huggingface.co/{rel['repo']}/resolve/{rel['revision']}/{name}", p)
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    if got != sha:
        sys.exit(f"SHA-256 mismatch for {name}: got {got}, expected {sha}")
    print(f"{name}: SHA-256 ok")
