"""One generic inbound endpoint: POST /sms {from, to, body}. The role comes from `to`.

SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway; a gateway adapter
is a thin mapping onto this endpoint and is not built.
"""
import os
import threading
import time
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.registry import Registry
from app.store import Store
from app import service
from app.engine import Protocol, ProtocolRejected

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Registry(os.environ.get("SNS_REGISTRY", ROOT / "config" / "registry.yaml"))
STORE = Store(os.environ.get("SNS_DB", ROOT / "data" / "sms.db"))

PROTOCOL_PATH = Path(os.environ.get("SNS_PROTOCOL", ROOT / "config" / "protocol.yaml"))
STATE = {"protocol": None, "load_error": None, "door_on": False, "cg_failed": [], "keyword_list": "v0",
         "encoder": None, "encoder_on": False, "extractors": None}
MODEL_DIR = os.environ.get("SNS_MODEL", str(ROOT / "models" / "onnx" / "trim10k_wq8"))


def load_protocol():
    """Load the protocol file; T1-T35 run on every load (a failure rejects the file and keeps the last valid one).
    CG1-CG18 and the lints run next; any red CG test switches the parent door off (F4)."""
    from app import cg_tests
    try:
        proto = Protocol.load(PROTOCOL_PATH)
    except (ProtocolRejected, Exception) as e:
        STATE["load_error"] = str(e)
        return STATE
    STATE["protocol"], STATE["load_error"] = proto, None
    from app import lexicon, must_stay_red
    from app.door import keyword_extractor
    # E2 replaces v0 live only if T1-T35 and CG1-CG18 pass with E2 loaded (prereg section 5, step 7)
    lexicon.use(lexicon.live_list({"name": "v0", "rows": lexicon.T_LIST, "k": lexicon.V0_K}))
    try:
        lexicon.use(lexicon.live_list(lexicon.e2_list()))
        if must_stay_red.run(proto) or cg_tests.run(proto):
            raise RuntimeError("E2 failed a must-stay-RED test")
    except Exception:
        lexicon.use(lexicon.live_list({"name": "v0", "rows": lexicon.T_LIST, "k": lexicon.V0_K}))
    STATE["keyword_list"] = lexicon.LIVE["name"]
    # the encoder reads parent text only; CG runs with it on and forced off; red with it on -> keyword list (rung 3)
    STATE["encoder"], STATE["encoder_on"] = None, False
    variants = [(STATE["keyword_list"] + ", encoder off", (keyword_extractor,))]
    try:
        if Path(MODEL_DIR, "model.onnx").exists():
            from app.encoder import Encoder
            enc = Encoder(MODEL_DIR)
            if not cg_tests.run(proto, variants=[(STATE["keyword_list"] + ", encoder on", (enc, keyword_extractor))]):
                STATE["encoder"], STATE["encoder_on"] = enc, True
    except Exception:
        pass
    STATE["extractors"] = (STATE["encoder"], keyword_extractor) if STATE["encoder_on"] else (keyword_extractor,)
    # board-only model (v2, calibrated): annotates the health worker's board; never the parent reply
    STATE["board_model"] = None
    try:
        if Path(ROOT, "config", "board_model.json").exists():
            from app.board_model import BoardModel
            STATE["board_model"] = BoardModel()
    except Exception:
        STATE["board_model"] = None
    try:
        STATE["cg_failed"] = cg_tests.run(proto, variants=variants)
    except Exception as e:
        STATE["cg_failed"] = [f"suite error: {type(e).__name__}"]
    STATE["door_on"] = not STATE["cg_failed"]
    # question layer (experimental): loaded after the CG suite, which therefore always runs with it off
    from app import questions as QL
    QL.load(proto.params)
    STATE["questions"] = {"on": QL.is_on(), "errors": QL.STATE["errors"]}
    return STATE


load_protocol()
app = FastAPI(title="SafetyNet-SMS")
LOCK = threading.Lock()   # one event at a time: the first committed event wins (D29)
# Public demo mode (Hugging Face Space): fictional data only, admin/diagnostic endpoints off, input size limit,
# a "Reset demo" button and an automatic reset after 30 minutes without activity. No SMS gateway exists in any mode.
PUBLIC = os.environ.get("SNS_PUBLIC") == "1"
MAX_BODY = 1000
IDLE_RESET_S = 30 * 60
ACTIVITY = {"last": time.time()}


# "Why this reply?" for the simulator page only. Computed AFTER the reply is sent, from the same parent policy the
# service uses; returned as a display field next to outbox rows; never part of any SMS (tests check both).
EXPLAIN = True
WHY = {}                 # outbox id -> one-line rule explanation for a parent reply
WHY_FIXED = {"CG_TIMEOUT": "Rules: the health worker did not reply in time → go now (safety net)",
             "CG_GO_NOW_U": "Rules: this number is not registered → go now; the CHA is told"}


def explain_parent(body, msg_id):
    from app import lexicon, textparse
    from app.door import DURATION_PARAM, SIGN_LABEL, parent_policy
    params = STATE["protocol"].params
    pol = parent_policy(body, params, STATE["extractors"])
    found = {}
    for sign, term, neg in lexicon.match_detail(body, lexicon.LIVE["rows"], lexicon.LIVE["k"]):
        if not neg and sign in pol.signs and sign not in found:
            found[sign] = term
    parts = [f"matched '{t}' ({SIGN_LABEL[s]})" for s, t in found.items()]
    for kind, days in textparse.parse(body).durations.items():
        if days >= params[DURATION_PARAM[kind][1]]:
            parts.append(f"{kind} for {days:g} days (long illness)")
    labels = {SIGN_LABEL[s] for s in pol.signs}
    parts += [r for r in pol.reasons if r not in labels]
    age = "under 2 months" if pol.u2m else f"{pol.age_months:g} months" if pol.age_months is not None else None
    if msg_id == "CG_GO_NOW":
        if parts:
            return "Rules: " + "; ".join(parts) + " → go now"
        return ("Rules: no age found → go now (fail-safe)" if age is None
                else "Rules: a different age in the open case → go now (new age)")
    if msg_id == "CG_TOLD":
        return ("Rules: no danger keyword matched; " + (f"age found: {age}" if age else "age from the earlier message")
                + " → health worker told")
    if msg_id == "CG_OOS":
        return f"Rules: out of scope ({pol.oos or 'not 2 to 59 months'}) → not for this service"
    return None


def why_for(row):
    """Display-only explanation for a parent reply: the rule line plus the board model's band for that case."""
    if not EXPLAIN or row.get("role") != "parent":
        return None
    if row["msg_id"].startswith("Q_"):                                  # question layer (experimental)
        return why_question(row)
    lines = [WHY.get(row["id"]) or WHY_FIXED.get(row["msg_id"])]
    case = STORE.case(row["case_code"]) if row.get("case_code") else None
    m = (case or {}).get("state", {}).get("model") or {}
    if m.get("band") == "possible":
        lines.append(f"Model (health worker's board only): possible, {m.get('sign')}")
    elif m.get("band") == "unsure":
        lines.append("Model (health worker's board only): unsure, please read")
    lines = [x for x in lines if x]
    return "\n".join(lines) or None


def why_question(row):
    if row["msg_id"] == "Q_ACK":
        return "Fixed acknowledgement. Answers 1 or 3 go to the facility as 'parent report, not checked'; 2 goes to the health worker's board only."
    case = STORE.case(row["case_code"]) if row.get("case_code") else None
    qid = row["msg_id"][2:]
    log = [e for e in ((case or {}).get("state", {}).get("q") or {}).get("log", []) if e["qid"] == qid and e["action"] == "approved"]
    if not log:
        return "Fixed bank question, approved by the health worker."
    return f"Bank question {qid}: drafted by the model, approved by CHP {log[-1]['by']}.\nWhy suggested: {log[-1]['reason']}"


def with_why(rows):
    return [dict(r, why=why_for(r)) if r.get("role") == "parent" else r for r in rows]


def reset_demo():
    from app.board_model import LOG
    with STORE.lock:
        for t in ("cases", "inbox", "outbox"):
            STORE.db.execute(f"DELETE FROM {t}")
    LOG.clear()
    WHY.clear()
    ACTIVITY["last"] = time.time()


def _timer():
    while True:
        try:
            with LOCK:
                service.tick(STORE, REGISTRY, STATE["protocol"], extractors=STATE["extractors"])
                if PUBLIC and time.time() - ACTIVITY["last"] > IDLE_RESET_S and STORE.last_outbox_id():
                    reset_demo()
        except Exception:
            pass
        time.sleep(1)


if os.environ.get("SNS_TIMER", "1") == "1":
    threading.Thread(target=_timer, daemon=True).start()


class QAction(BaseModel):
    chp: str
    code: str
    qid: str
    action: str


@app.post("/chw/question")
def chw_question(a: QAction):
    """Health-worker endpoint (question layer, experimental): approve or decline one suggested bank question."""
    from app import qflow
    with LOCK:
        if STATE["protocol"] is None or a.chp not in REGISTRY.chp_by_phone:
            raise HTTPException(status_code=404)
        before = STORE.last_outbox_id()
        r = qflow.chw_action(STORE, REGISTRY, STATE["protocol"], a.chp, a.code, a.qid, a.action)
        return {**r, "replies": with_why(STORE.outbox_since(before))}


class Inbound(BaseModel):
    sender: str = Field(alias="from")
    to: str
    body: str


@app.post("/sms")
def sms(msg: Inbound):
    role = REGISTRY.role(msg.to)
    if PUBLIC and len(msg.body) > MAX_BODY:
        raise HTTPException(status_code=413, detail=f"demo limit: at most {MAX_BODY} characters")
    ACTIVITY["last"] = time.time()
    with LOCK:
        before = STORE.last_outbox_id()
        STORE.log_in(msg.sender, msg.to, role, msg.body)
        if role == "parent" and not STATE["door_on"]:
            service.door_off(STORE, REGISTRY, msg.sender)   # fail-safe: fixed go-now + CHA copy, never silence
        elif role is not None:
            service.handle(STORE, REGISTRY, STATE["protocol"], role, msg.sender, msg.body, extractors=STATE["extractors"],
                           board_model=STATE.get("board_model"))
        replies = STORE.outbox_since(before)
        if EXPLAIN and role == "chp":
            for r in replies:
                if r["role"] == "parent" and r["msg_id"] == "CG_GO_NOW":
                    WHY[r["id"]] = "Rules: the health worker's checklist answer matched a RED rule → go now"
        if EXPLAIN and role == "parent" and STATE["door_on"]:
            for r in replies:
                if r["role"] == "parent":
                    try:
                        w = explain_parent(msg.body, r["msg_id"])
                    except Exception:
                        w = None
                    if w:
                        WHY[r["id"]] = w
        return {"role": role, "replies": with_why(replies)}


@app.get("/outbox")
def outbox(since: int = 0):
    return with_why(STORE.outbox_since(since))


@app.get("/keyword_terms")
def keyword_terms(sign: str):
    """Read-only: the live keyword-list terms for one sign (the simulator's rule-check card shows them)."""
    from app import lexicon
    return {"sign": sign, "terms": list(lexicon.LIVE["rows"].get(sign, []))}


@app.get("/inbox")
def inbox(since: int = 0):
    return STORE.inbox_since(since)


@app.get("/board")
def case_board(phone: str):
    from app import board
    if STATE["protocol"] is None or phone not in REGISTRY.chp_by_phone:
        return []
    with LOCK:
        return board.board(STORE, phone, STATE["protocol"])


@app.post("/demo/reset")
def demo_reset():
    """Clears every case, message and log line (the registry, protocol and models are untouched)."""
    with LOCK:
        reset_demo()
    return {"ok": True}


@app.post("/demo/fire-timeouts")
def demo_fire_timeouts():
    """Demo shortcut: fire every pending due time now, instead of waiting for the 60 s demo timeout."""
    with LOCK:
        n = service.tick(STORE, REGISTRY, STATE["protocol"], now=time.time() + 10 ** 6, extractors=STATE["extractors"])
    return {"fired": n}


@app.post("/admin/reload")
def reload():
    if PUBLIC:
        raise HTTPException(status_code=404)
    st = load_protocol()
    return {"loaded": st["load_error"] is None, "error": st["load_error"], "door_on": st["door_on"],
            "keyword_list": st["keyword_list"], "encoder_on": st["encoder_on"], "model": MODEL_DIR,
            "board_model": bool(st.get("board_model")),
            "cg_failed": st["cg_failed"],
            "live": st["protocol"].cfg["profile"]["id"] if st["protocol"] else None}


@app.get("/config")
def config():
    r = REGISTRY
    return {"lines": r.lines, "parents": list(r.parents), "chps": [c["phone"] for c in r.chps.values()],
            "facility": r.facility["phone"], "facilities": [{"phone": f["phone"], "name": f["name"]} for f in r.facilities.values()],
            "cha": [c["phone"] for c in r.cha.values()], "door_on": STATE["door_on"], "public": PUBLIC,
            "questions_on": STATE.get("questions", {}).get("on", False)}


@app.get("/")
def simulator():
    return FileResponse(ROOT / "sim" / "index.html")


# ---------- P4: the shipped board model in a phone browser (onnxruntime-web, single-threaded WASM) ----------
PHONE_FILES = {"model.onnx": None, "tokenizer.json": None, "board_model.json": ROOT / "config" / "board_model.json",
               "ydev.json": None}


def _board_dir():
    import json as _json
    return ROOT / _json.loads((ROOT / "config" / "board_model.json").read_text())["model_dir"]


@app.get("/phone")
def phone_page():
    return FileResponse(ROOT / "sim" / "phone.html")


@app.get("/phone/ort/{name}")
def phone_ort(name: str):
    p = ROOT / "sim" / "ort" / name
    if p.parent != ROOT / "sim" / "ort" or not p.exists():
        return {"error": "not found"}
    mt = "application/wasm" if name.endswith(".wasm") else "text/javascript" if name.endswith((".mjs", ".js")) else None
    return FileResponse(p, media_type=mt)


@app.get("/phone/{name}")
def phone_file(name: str):
    import json as _json
    if name in ("model.onnx", "tokenizer.json"):
        return FileResponse(_board_dir() / name)
    if name == "board_model.json":
        return FileResponse(ROOT / "config" / "board_model.json")
    if name == "ydev.json":                     # development set only (never a test set): 50 messages for timing and parity
        rows = [_json.loads(l) for l in open(ROOT / "data" / "y_dev.jsonl", encoding="utf-8")][:50]
        return [{"id": r["id"], "message": r["message"]} for r in rows]
    return {"error": "not found"}


@app.post("/phone/report")
def phone_report(r: dict = Body(...)):
    if PUBLIC:
        raise HTTPException(status_code=404)
    import json as _json
    import time as _time
    r["received"] = _time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ROOT / "data" / "phone_report.jsonl", "a", encoding="utf-8") as fh:
        fh.write(_json.dumps(r) + "\n")
    return {"ok": True}


@app.post("/phone/parity")
def phone_parity(rows: list = Body(...)):
    """Compare the phone's token ids, raw head flags and board band with the Pi's, message by message."""
    if PUBLIC:
        raise HTTPException(status_code=404)
    import json as _json
    import numpy as np
    from app.board_model import BoardModel
    from app.encoder import HEADS
    bm = STATE.get("board_model") or BoardModel()
    msgs = {r["id"]: r["message"] for r in (_json.loads(l) for l in open(ROOT / "data" / "y_dev.jsonl", encoding="utf-8"))}
    out = {"n": len(rows), "tokens_match": 0, "flags_match": 0, "bands_match": 0, "max_abs_dp": 0.0, "mismatch": []}
    for r in rows:
        text = msgs[r["id"]]
        ids = bm.enc.tok.encode(text).ids
        p = bm.enc.probs(text)
        raw = [h for h, v in zip(HEADS, p) if v >= 0.5]
        band = bm.band(text)["band"]
        ok_t, ok_f, ok_b = ids == r["ids"], raw == r["raw"], band == r["band"]
        out["tokens_match"] += ok_t
        out["flags_match"] += ok_f
        out["bands_match"] += ok_b
        out["max_abs_dp"] = round(max(out["max_abs_dp"], float(np.abs(np.array(r["probs"]) - p).max())), 5)
        if not (ok_t and ok_f and ok_b):
            out["mismatch"].append(f"{r['id']} (tokens {ok_t}, flags {ok_f}, band {ok_b})")
    (ROOT / "data" / "phone_parity.json").write_text(_json.dumps(out, indent=1))
    return out



@app.get("/log")
def live_log():
    """Live inset for the demo: model time and band per parent message; CHP ids only, no phone numbers or text."""
    from app.board_model import LOG
    out = []
    for e in list(LOG)[-8:]:
        chp = REGISTRY.chp_by_phone.get(e["chp_phone"]) if e["chp_phone"] else None
        out.append({"time": e["time"], "code": e["code"], "chp": f"CHP {chp['id']}" if chp else "no CHP",
                    "model_ms": e["model_ms"], "band": e["band"]})
    return out
