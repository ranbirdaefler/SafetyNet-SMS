"""One generic inbound endpoint: POST /sms {from, to, body}. The role comes from `to`.

SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway; a gateway adapter
is a thin mapping onto this endpoint and is not built.
"""
import os
import threading
import time
from pathlib import Path

from fastapi import FastAPI
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
STATE = {"protocol": None, "load_error": None, "door_on": False, "cg_failed": []}


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
    try:
        STATE["cg_failed"] = cg_tests.run(proto)
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
                service.tick(STORE, REGISTRY, STATE["protocol"])
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
            service.handle(STORE, REGISTRY, STATE["protocol"], role, msg.sender, msg.body)
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
