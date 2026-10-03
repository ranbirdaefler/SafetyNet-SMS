"""Swahili drafts for the question bank (gpt-5.5), with an independent back-translation of every text so a reviewer
can check each option's polarity. Writes gen/questions_sw.json; the reviewed texts are copied into
config/questions.yaml by hand after Florian's approval. Not native-reviewed."""
import json
import sys
from pathlib import Path

import yaml
from openai import OpenAI

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
MODEL = "gpt-5.5"
client = OpenAI()

TRANSLATE = ("Translate this SMS for a parent in rural western Kenya into simple, everyday Kenyan Swahili. Keep the "
             "meaning exact, including the reply numbers 1, 2 and 3 and what each number means; keep option 1 as the "
             "first option. Use plain words a parent with little schooling understands. No extra words, no advice. "
             "At most {limit} characters, using only the basic GSM 7-bit alphabet (no curly quotes). Output only the SMS.")
BACK = ("Translate this Swahili SMS into English, word for word as far as possible, keeping the reply numbers and what "
        "each means. Output only the translation.")


def call(instr, text):
    r = client.responses.create(model=MODEL, instructions=instr, input=text)
    return r.output_text.strip()


def main():
    bank = yaml.safe_load((ROOT / "config" / "questions.yaml").read_text(encoding="utf-8"))
    from app.engine import Protocol
    params = Protocol.load(ROOT / "config" / "protocol.yaml", run_suite=False).params
    prefix = bank["prefix_referred"]["en"]
    items = {"prefix_referred": (prefix, 60), "ack_referred": (bank["ack_referred"]["en"], 90)}
    for q in bank["questions"]:
        en = q["en"].format(**params)
        limit = 160 - (len(prefix) + 1 if q["kind"] == "prearrival" else 0) - 6     # room for the Swahili prefix
        items[q["id"]] = (en, limit)
    out = {}
    for k, (en, limit) in items.items():
        sw = call(TRANSLATE.format(limit=limit), en)
        out[k] = {"en": en, "sw": sw, "back": call(BACK, sw), "sw_len": len(sw), "limit": limit}
        print(k, len(sw), "/", limit, flush=True)
    (ROOT / "gen" / "questions_sw.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
