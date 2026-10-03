"""v3 training data (gpt-5.5 only; prompts committed before the calls). Labels come from the cards.
- contrast: "sign present" / "same message, sign denied" pairs, 5 caregiver signs x Swahili / English / code-mixed,
  plus extra "very sleepy" denials (D2: sleepy denials were flagged 8/8). Present -> that sign; denied -> no sign.
- durneg: duration hard negatives under the cut-offs (cough 2-13 d, diarrhoea 2-13 d, fever 1-6 d), varied phrasing,
  numbers and relative time (D3: v2's commonest needless trip). Label: no sign.
Usage: python gen/v3/gen_v3.py
"""
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "gen"))
from cards import HEADS  # noqa: E402

load_dotenv(ROOT / ".env")
client = OpenAI()
CONTRAST = (Path(__file__).parent / "contrast_prompt.txt").read_text(encoding="utf-8")
CAREGIVER = (ROOT / "prompts" / "caregiver_system.txt").read_text(encoding="utf-8")
SIGNS = {"convulsions": "fits / convulsions (degedege)", "not_drink_feed": "cannot drink or breastfeed at all",
         "vomits_everything": "vomits everything", "sleepy_unconscious": "unusually sleepy, hard to wake",
         "blood_stool": "blood in the stool"}
PAIR = {"type": "object", "properties": {"present": {"type": "string"}, "denied": {"type": "string"}},
        "required": ["present", "denied"], "additionalProperties": False}
ONE = {"type": "object", "properties": {"texts": {"type": "array", "items": {"type": "string"}}},
       "required": ["texts"], "additionalProperties": False}
rng = random.Random(8008)


def call(instr, user, schema):
    r = client.responses.create(model="gpt-5.5", instructions=instr, input=user, reasoning={"effort": "low"},
                                text={"format": {"type": "json_schema", "name": "x", "schema": schema, "strict": True}})
    return json.loads(r.output_text)


def vec(signs):
    return [int(h in signs) for h in HEADS]


def contrast_cards():
    cards = []
    for s in SIGNS:
        for lang in ("Swahili", "English", "code-mixed (Swahili and English in one message)"):
            for _ in range(16):
                cards.append({"sign": s, "lang": lang})
    for _ in range(40):
        cards.append({"sign": "sleepy_unconscious", "lang": rng.choice(["Swahili", "English", "code-mixed (Swahili and English in one message)"])})
    for c in cards:
        c["age"] = rng.randint(2, 59)
        c["mild"] = rng.choice(["a mild fever", "a runny nose", "poor appetite", "a rash", "a little cough", ""])
    return cards


def durneg_cards():
    cards = []
    for _ in range(150):
        kind = rng.choice(["cough", "diarrhoea (loose watery stools)", "fever (hot body)"])
        lo, hi = {"cough": (2, 13), "fever (hot body)": (1, 6)}.get(kind, (2, 13))
        cards.append({"kind": kind, "days": rng.randint(lo, hi), "age": rng.randint(2, 59),
                      "lang": rng.choice(["Swahili", "English", "code-mixed"]),
                      "relative": rng.random() < 0.3, "casual": rng.random() < 0.3})
    return cards


def one_pair(c):
    user = (f"Danger sign: {SIGNS[c['sign']]}\nLanguage: {c['lang']}\nAge: {c['age']} months\n"
            + (f"Also mention: {c['mild']}\n" if c["mild"] else "") + "Output only the JSON.")
    return {**c, **call(CONTRAST, user, PAIR)}


def one_durneg(c):
    lines = ["Case card:", f"- Language: {c['lang']}", f"- Age: the child is {c['age']} months old",
             f"- {c['kind']} for {c['days']} days" + (" (say it with relative time)" if c["relative"] else ""),
             "- No other symptom"]
    if c["casual"]:
        lines.append("- Style: casual")
    lines += ["- Number of SMS: one", "Write the SMS now. Output only the JSON."]
    return {**c, "texts": call(CAREGIVER, "\n".join(lines), ONE)["texts"]}


def main():
    with ThreadPoolExecutor(12) as ex:
        pairs = list(ex.map(one_pair, contrast_cards()))
        durs = list(ex.map(one_durneg, durneg_cards()))
    out = []
    for i, p in enumerate(pairs):
        out.append({"id": f"v3c-{i:03d}p", "message": p["present"], "present": vec([p["sign"]]), "category": "danger", "source": "contrast"})
        out.append({"id": f"v3c-{i:03d}d", "message": p["denied"], "present": vec([]), "category": "no_danger", "source": "contrast_denial"})
    for i, d in enumerate(durs):
        out.append({"id": f"v3d-{i:03d}", "message": " || ".join(d["texts"]), "present": vec([]), "category": "no_danger", "source": "duration_negative"})
    (ROOT / "data" / "v3_gen.jsonl").write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n", encoding="utf-8")
    print(len(pairs), "pairs,", len(durs), "duration negatives")


if __name__ == "__main__":
    main()
