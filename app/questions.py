"""Question layer (EXPERIMENTAL, after results): the health worker approves fixed bank questions to a parent.

Bank: config/questions.yaml, validated on load. Any lint error switches the layer OFF (like the door flag), and the
switch is also off when the bank says enabled: false or SNS_QUESTIONS=0. With the layer off nothing here changes any
existing behaviour. Safety rules: quorum/rounds/reconvene/2026-10-03-question-layer-safety.md (M1-M8, E1-E7).
"""
import os
import re
from pathlib import Path

import yaml

from app import messages as M

ROOT = Path(__file__).resolve().parent.parent
GSM = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
          "abcdefghijklmnopqrstuvwxyzäöñüà")
GSM_EXT = set("^{}\\[~]|€")
SIGNS = {"convulsions", "not_drink_feed", "vomits_everything", "sleepy_unconscious", "blood_stool", "cough_long",
         "diarrhoea_long", "fever_long"}
# review section 4: never in a bank question (whole words, EN; medicine words come from the bank's blocked lists)
NEVER = ["serious", "worried", "normal", "fine", "ok", "okay", "better", "wait", "first", "before you go", "until",
         "how is the child", "pneumonia", "malaria", "dysentery", "diagnosis"]
STATE = {"on": False, "bank": None, "errors": [], "by_id": {}}


def segments(text):
    """SMS segments: GSM-7 (160 / 153) or UCS-2 (70 / 67)."""
    if all(c in GSM or c in GSM_EXT for c in text):
        n = len(text) + sum(c in GSM_EXT for c in text)
        return 1 if n <= 160 else -(-n // 153)
    return 1 if len(text) <= 70 else -(-len(text) // 67)


def has_word(text, words):
    t = " " + re.sub(r"[^\w']+", " ", text.lower()) + " "
    return [w for w in words if " " + w.lower() + " " in t]


def lint(bank, params):
    errs = []
    blocked = bank.get("blocked", {})
    medicine = blocked.get("medicine_en", []) + blocked.get("medicine_sw", [])
    pre = bank.get("prefix_referred", {})
    if not pre.get("en") or not pre.get("sw"):
        errs.append("prefix_referred: en and sw required")
    for k in ("ack_referred",):
        for lang in ("en", "sw"):
            t = (bank.get(k) or {}).get(lang)
            if not t:
                errs.append(f"{k}: {lang} missing")
            elif segments(t) > 1:
                errs.append(f"{k}: {lang} over 1 segment")
    ids = set()
    for q in bank.get("questions", []):
        qid = q.get("id", "?")
        if qid in ids:
            errs.append(f"{qid}: duplicate id")
        ids.add(qid)
        if q.get("kind") not in ("check", "prearrival"):
            errs.append(f"{qid}: kind must be check or prearrival")
        if q.get("sign") not in SIGNS:
            errs.append(f"{qid}: unknown sign")
        if q.get("kind") == "prearrival" and not set(q.get("trigger_signs") or []) <= SIGNS | set():
            errs.append(f"{qid}: unknown trigger sign")
        if q.get("kind") == "prearrival" and not q.get("trigger_signs"):
            errs.append(f"{qid}: prearrival needs trigger_signs")
        labels = q.get("labels") or {}
        if sorted(int(k) for k in labels) != [1, 2, 3]:
            errs.append(f"{qid}: labels 1, 2, 3 required (1 = danger)")
        if not q.get("source"):
            errs.append(f"{qid}: WHO/UNICEF source required")
        for lang in ("en", "sw"):
            t = q.get(lang)
            if not t:
                errs.append(f"{qid}: {lang} missing")
                continue
            try:
                t = t.format(**params)
            except Exception:
                errs.append(f"{qid}: {lang} unknown placeholder")
                continue
            if not re.search(r"\b1\b.*\b2\b.*\b3\b", t, flags=re.S):
                errs.append(f"{qid}: {lang} must offer 1, 2, 3 in that order")
            full = (pre.get(lang, "") + " " + t) if q.get("kind") == "prearrival" else t
            if segments(full) > 1:
                errs.append(f"{qid}: {lang} over 1 segment (with the prefix on referred cases)")
            if has_word(t, medicine):
                errs.append(f"{qid}: {lang} medicine/dose word")
            if lang == "en" and has_word(t, NEVER):
                errs.append(f"{qid}: en banned word {has_word(t, NEVER)}")
            if re.search(r"\b0\b", t):
                errs.append(f"{qid}: {lang} must not offer 0")
    if not bank.get("blocked", {}).get("refuse_text"):
        errs.append("blocked.refuse_text missing")
    return errs


def load(params, path=None, force=None):
    """Load and lint the bank; register the fixed Q_ texts on the parent allowlist only when the layer is on."""
    p = Path(path) if path else ROOT / "config" / "questions.yaml"
    STATE.update(on=False, bank=None, errors=[], by_id={})
    for k in [k for k in M.QL_TEMPLATES]:
        del M.QL_TEMPLATES[k]
    try:
        bank = yaml.safe_load(p.read_text(encoding="utf-8"))
    except Exception as e:
        STATE["errors"] = [f"bank not readable: {type(e).__name__}"]
        return STATE
    errs = lint(bank, params)
    on = bank.get("enabled", False) if force is None else force
    if os.environ.get("SNS_QUESTIONS") == "0":
        on = False
    STATE.update(bank=bank, errors=errs, by_id={q["id"]: q for q in bank.get("questions", [])})
    if errs or not on:
        return STATE
    pre = bank["prefix_referred"]
    for q in bank["questions"]:
        if q.get("approved") is not True:                 # only texts Florian approved reach the allowlist
            continue
        texts = {lang: q[lang].format(**params) for lang in ("en", "sw")}
        variants = list(texts.values()) + [pre[lang] + " " + texts[lang] for lang in ("en", "sw")]
        M.QL_TEMPLATES["Q_" + q["id"]] = variants
    M.QL_TEMPLATES["Q_ACK"] = [bank["ack_referred"]["en"], bank["ack_referred"]["sw"]]
    STATE["on"] = True
    return STATE


def approved_questions():
    return [q for q in (STATE["bank"] or {}).get("questions", []) if q.get("approved") is True]


def blocked_hits(text):
    """Review E2 for her own messages: medicine / dose, change-of-plan and reassurance words, EN and SW lists applied
    to every message (code-mixing); *_stems_sw match inside any word. Returns the hits (empty = allowed)."""
    b = (STATE["bank"] or {}).get("blocked", {})
    words = [w for k, v in b.items() if isinstance(v, list) and not k.endswith("_stems_sw") for w in v]
    stems = [w for k, v in b.items() if isinstance(v, list) and k.endswith("_stems_sw") for w in v]
    t = text.lower().replace("’", "'")
    hits = has_word(t, words)
    toks = re.findall(r"[\w']+", t)
    hits += [s for s in stems if any(s in tok for tok in toks)]
    return hits


def is_on():
    return STATE["on"]


def question(qid):
    return STATE["by_id"].get(qid)


def text_for(qid, lang, referred, params):
    q = STATE["by_id"][qid]
    lang = lang if lang in ("en", "sw") else "sw"
    t = q[lang].format(**params)
    return (STATE["bank"]["prefix_referred"][lang] + " " + t) if referred else t


def ack_text(lang):
    lang = lang if lang in ("en", "sw") else "sw"
    return STATE["bank"]["ack_referred"][lang]


BARE = {"1": 1, "2": 2, "3": 3, "moja": 1, "mbili": 2, "tatu": 3}


def parse_answer(body):
    """A bare 1/2/3 (or moja/mbili/tatu), allowing surrounding spaces and one trailing full stop. Anything else
    (yes/no/ndiyo/hapana, '1 2', free text) returns None; the caller treats it as 'not sure' (review M5)."""
    t = body.strip().lower().rstrip(".")
    return BARE.get(t)
