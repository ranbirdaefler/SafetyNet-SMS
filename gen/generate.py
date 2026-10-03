"""Generate caregiver-voice SMS from cards.

Families (PREREGISTRATION.md section 3): X train and Y-dev from GPT (gpt-5.5); every test set from Claude (claude-opus-5-5).
Sealed splits (y_test, set_b) never print message text: only counts and error class names.

Usage: python gen/generate.py {x_train|y_dev|y_test|set_b} [--limit N]
"""
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
import aug_cards as A
import cards as C

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
SYSTEM = (ROOT / "prompts" / "caregiver_system.txt").read_text(encoding="utf-8")

GPT_MODEL = "gpt-5.5"
CLAUDE_MODEL = "claude-opus-5-5"
SCHEMA = {
    "type": "object",
    "properties": {"texts": {"type": "array", "items": {"type": "string"}}},
    "required": ["texts"],
    "additionalProperties": False,
}

OUT = {
    "x_train": ROOT / "data" / "x_train.jsonl",
    "x_aug": ROOT / "data" / "x_aug.jsonl",
    "y_dev": ROOT / "data" / "y_dev.jsonl",
    "y_test": ROOT / "tests" / "y_test.jsonl",
    "set_b": ROOT / "tests" / "caregiver_set_b.csv",
}
SEALED = {"y_test", "set_b"}
FAMILY = {"x_aug": "gpt", "x_train": "gpt", "y_dev": "gpt", "y_test": "claude", "set_b": "claude"}


def call_gpt(client, user):
    r = client.responses.create(
        model=GPT_MODEL,
        instructions=SYSTEM,
        input=user,
        reasoning={"effort": "low"},
        text={"format": {"type": "json_schema", "name": "sms", "schema": SCHEMA, "strict": True}},
    )
    return json.loads(r.output_text)["texts"]


def call_claude(client, user):
    r = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        system=SYSTEM,
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": user}],
    )
    if r.stop_reason == "refusal":
        raise RuntimeError("refusal")
    text = "".join(b.text for b in r.content if b.type == "text")
    return json.loads(text)["texts"]


def one(fn, client, card):
    want = 2 if "two texts" in card["style"] else 1
    last = None
    for attempt in range(4):
        try:
            texts = [t.strip() for t in fn(client, A.render(card) if card["id"].startswith("x_aug") else C.render(card))]
            if len(texts) == want and all(texts):
                return texts
            last = "wrong_text_count"
        except Exception as e:  # class name only: never echo content
            last = type(e).__name__
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(last)


def main():
    split = sys.argv[1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    cards = (C.grid_b_cards() if split == "set_b" else A.all_cards() if split == "x_aug"
             else C.sample_split(split, *C.SPLITS[split]))
    if limit:
        cards = cards[:limit]
    if FAMILY[split] == "gpt":
        from openai import OpenAI
        client, fn, model, workers = OpenAI(), call_gpt, GPT_MODEL, 16
    else:
        import anthropic
        client, fn, model, workers = anthropic.Anthropic(), call_claude, CLAUDE_MODEL, 8

    results, errors = {}, {}
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(one, fn, client, c): c for c in cards}
        for i, f in enumerate(as_completed(futs), 1):
            c = futs[f]
            try:
                results[c["id"]] = f.result()
            except Exception as e:
                errors[c["id"]] = str(e)
            if i % 50 == 0:
                print(f"{split}: {i}/{len(cards)} done, {len(errors)} errors", flush=True)

    out = OUT[split]
    if limit:
        out = out.with_name(out.stem + f".limit{limit}" + out.suffix)
    out.parent.mkdir(parents=True, exist_ok=True)
    if split == "set_b":
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["id", "label_line", "message"])
            for c in cards:
                if c["id"] in results:
                    label = f"{c['id']} {'danger' if c['category'] == 'danger' else 'no danger'}: {c['signs'][0] if c['signs'] else 'none'}"
                    w.writerow([c["id"], label, " || ".join(results[c["id"]])])
    else:
        with open(out, "w", encoding="utf-8") as fh:
            for c in cards:
                if c["id"] in results:
                    rec = {k: v for k, v in c.items()}
                    rec["texts"] = results[c["id"]]
                    rec["message"] = " || ".join(results[c["id"]])
                    rec["generator"] = model
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    meta = {"split": split, "generator": model, "cards": len(cards), "written": len(results),
            "errors": errors, "finished": time.strftime("%Y-%m-%d %H:%M:%S %Z")}
    (out.parent / (out.stem + ".meta.json")).write_text(json.dumps(meta, indent=1))
    print(f"{split}: wrote {len(results)} of {len(cards)} to {out.relative_to(ROOT)}; {len(errors)} errors"
          + ("" if split in SEALED else f": {errors}"))


if __name__ == "__main__":
    main()
