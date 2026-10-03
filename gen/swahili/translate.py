"""Swahili Level 1 drafts (not used by the app): the 5 parent strings translated by gpt-5.5. Needs native review."""
import json
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from app import messages as M  # noqa: E402

IDS = ["CG_GO_NOW", "CG_GO_NOW_U", "CG_TOLD", "CG_TIMEOUT", "CG_OOS"]
SCHEMA = {"type": "object", "properties": {"translations": {"type": "object", "properties": {i: {"type": "string"} for i in IDS},
          "required": IDS, "additionalProperties": False}}, "required": ["translations"], "additionalProperties": False}
prompt = (Path(__file__).parent / "prompt.txt").read_text(encoding="utf-8")
src = {i: M.PARENT_ALLOWLIST[i] for i in IDS}
r = OpenAI().responses.create(model="gpt-5.5", instructions=prompt, input=json.dumps(src, ensure_ascii=False),
                              reasoning={"effort": "medium"},
                              text={"format": {"type": "json_schema", "name": "sw", "schema": SCHEMA, "strict": True}})
out = json.loads(r.output_text)["translations"]
(Path(__file__).parent / "drafts.json").write_text(json.dumps({"model": "gpt-5.5", "english": src, "swahili": out},
                                                              indent=1, ensure_ascii=False), encoding="utf-8")
print("ok")
