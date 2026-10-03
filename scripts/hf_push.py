"""Push the board model (model repo) and the demo Space to Hugging Face. Reads HF_TOKEN from .env; never prints it.
Usage: python scripts/hf_push.py model | space <git ref>"""
import hashlib
import json
import sys
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
env = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))
api = HfApi(token=env["HF_TOKEN"].strip().strip('"'))
rel = json.loads((ROOT / "config" / "model_release.json").read_text())
SPACE = "ranbirr1/safetynet-sms"

if sys.argv[1] == "model":
    cfg = json.loads((ROOT / rel["board_config"]).read_text())
    src = ROOT / cfg["model_dir"]
    for name, sha in rel["sha256"].items():
        assert hashlib.sha256((src / name).read_bytes()).hexdigest() == sha, name
    api.create_repo(rel["repo"], repo_type="model", exist_ok=True)
    api.upload_file(path_or_fileobj=str(ROOT / "hf" / "model_card.md"), path_in_repo="README.md", repo_id=rel["repo"])
    for name in rel["sha256"]:
        api.upload_file(path_or_fileobj=str(src / name), path_in_repo=name, repo_id=rel["repo"],
                        commit_message=f"{name} (v3 board file)")
    print("model repo:", [f for f in api.list_repo_files(rel["repo"])])
elif sys.argv[1] == "space":
    ref = sys.argv[2]
    api.create_repo(SPACE, repo_type="space", space_sdk="docker", exist_ok=True)
    api.add_space_variable(SPACE, "REF", ref)
    api.upload_file(path_or_fileobj=str(ROOT / "space" / "README.md"), path_in_repo="README.md", repo_id=SPACE, repo_type="space")
    api.upload_file(path_or_fileobj=str(ROOT / "space" / "Dockerfile"), path_in_repo="Dockerfile", repo_id=SPACE,
                    repo_type="space", commit_message=f"build from {ref}")
    print("space files:", api.list_repo_files(SPACE, repo_type="space"), "REF =", ref)
elif sys.argv[1] == "status":
    rt = api.get_space_runtime(SPACE)
    print(rt.stage, rt.hardware)
