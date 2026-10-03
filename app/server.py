"""One generic inbound endpoint: POST /sms {from, to, body}. The role comes from `to`.

SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway; a gateway adapter
is a thin mapping onto this endpoint and is not built.
"""
import os
import threading
import time
from pathlib import Path

from fastapi import Body, FastAPI
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
    lexicon.use({"name": "v0", "rows": lexicon.T_LIST, "k": lexicon.V0_K})
    try:
        lexicon.use(lexicon.e2_list())
        if must_stay_red.run(proto) or cg_tests.run(proto):
            raise RuntimeError("E2 failed a must-stay-RED test")
    except Exception:
        lexicon.use({"name": "v0", "rows": lexicon.T_LIST, "k": lexicon.V0_K})
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
    return STATE


load_protocol()
app = FastAPI(title="SafetyNet-SMS")
LOCK = threading.Lock()   # one event at a time: the first committed event wins (D29)


def _timer():
    while True:
        try:
            with LOCK:
                service.tick(STORE, REGISTRY, STATE["protocol"], extractors=STATE["extractors"])
        except Exception:
            pass
        time.sleep(1)


if os.environ.get("SNS_TIMER", "1") == "1":
    threading.Thread(target=_timer, daemon=True).start()


class Inbound(BaseModel):
    sender: str = Field(alias="from")
    to: str
    body: str


@app.post("/sms")
def sms(msg: Inbound):
    role = REGISTRY.role(msg.to)
    with LOCK:
        before = STORE.last_outbox_id()
        STORE.log_in(msg.sender, msg.to, role, msg.body)
        if role == "parent" and not STATE["door_on"]:
            service.door_off(STORE, REGISTRY, msg.sender)   # fail-safe: fixed go-now + CHA copy, never silence
        elif role is not None:
            service.handle(STORE, REGISTRY, STATE["protocol"], role, msg.sender, msg.body, extractors=STATE["extractors"],
                           board_model=STATE.get("board_model"))
        return {"role": role, "replies": STORE.outbox_since(before)}


@app.get("/outbox")
def outbox(since: int = 0):
    return STORE.outbox_since(since)


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


@app.post("/admin/reload")
def reload():
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
            "cha": [c["phone"] for c in r.cha.values()], "door_on": STATE["door_on"]}


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
    import json as _json
    import time as _time
    r["received"] = _time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ROOT / "data" / "phone_report.jsonl", "a", encoding="utf-8") as fh:
        fh.write(_json.dumps(r) + "\n")
    return {"ok": True}


@app.post("/phone/parity")
def phone_parity(rows: list = Body(...)):
    """Compare the phone's token ids, raw head flags and board band with the Pi's, message by message."""
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
