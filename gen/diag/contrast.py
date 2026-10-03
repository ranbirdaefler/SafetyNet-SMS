"""D2 (diagnosis, not training): 40 contrast pairs "sign present" / "same message, sign denied", gpt-5.5, Y-dev style.
5 caregiver signs x 2 languages (Swahili, English) x 4 cards, seeded. Prompt committed before the call."""
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
PROMPT = (Path(__file__).parent / "contrast_prompt.txt").read_text(encoding="utf-8")
SIGNS = {"convulsions": "fits / convulsions (degedege)", "not_drink_feed": "cannot drink or breastfeed at all",
         "vomits_everything": "vomits everything", "sleepy_unconscious": "unusually sleepy, hard to wake",
         "blood_stool": "blood in the stool"}
SCHEMA = {"type": "object", "properties": {"present": {"type": "string"}, "denied": {"type": "string"}},
          "required": ["present", "denied"], "additionalProperties": False}
rng = random.Random(6006)
cards = []
for s, desc in SIGNS.items():
    for lang in ("Swahili", "English"):
        for k in range(4):
            cards.append({"id": f"cp-{len(cards) + 1:02d}", "sign": s, "lang": lang, "age_months": rng.randint(2, 59),
                          "mild": rng.choice(["a mild fever", "a runny nose", "poor appetite", "a rash", ""])})
client = OpenAI()


def one(c):
    user = (f"Danger sign: {SIGNS[c['sign']]}\nLanguage: {c['lang']}\nAge: {c['age_months']} months\n"
            + (f"Also mention: {c['mild']}\n" if c["mild"] else "") + "Output only the JSON.")
    r = client.responses.create(model="gpt-5.5", instructions=PROMPT, input=user, reasoning={"effort": "low"},
                                text={"format": {"type": "json_schema", "name": "pair", "schema": SCHEMA, "strict": True}})
    return {**c, **json.loads(r.output_text)}


with ThreadPoolExecutor(8) as ex:
    out = list(ex.map(one, cards))
(ROOT / "data" / "diag_contrast_pairs.jsonl").write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n",
                                                         encoding="utf-8")
print(len(out), "pairs")
