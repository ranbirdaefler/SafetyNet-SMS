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
STATE = {"protocol": None, "load_error": None}


def load_protocol():
    """Load the protocol file; must-stay-RED tests run on every load. A rejected file keeps the last valid one."""
    try:
        STATE["protocol"] = Protocol.load(PROTOCOL_PATH)
        STATE["load_error"] = None
    except (ProtocolRejected, Exception) as e:
        STATE["load_error"] = str(e)
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
        if role is not None:
            service.handle(STORE, REGISTRY, STATE["protocol"], role, msg.sender, msg.body)
        return {"role": role, "replies": STORE.outbox_since(before)}


@app.get("/outbox")
def outbox(since: int = 0):
    return STORE.outbox_since(since)


@app.get("/inbox")
def inbox(since: int = 0):
    return STORE.inbox_since(since)


@app.post("/admin/reload")
def reload():
    st = load_protocol()
    return {"loaded": st["load_error"] is None, "error": st["load_error"],
            "live": st["protocol"].cfg["profile"]["id"] if st["protocol"] else None}


@app.get("/config")
def config():
    r = REGISTRY
    return {"lines": r.lines, "parents": list(r.parents), "chps": [c["phone"] for c in r.chps.values()],
            "facility": r.facility["phone"], "cha": [c["phone"] for c in r.cha.values()]}


@app.get("/")
def simulator():
    return FileResponse(ROOT / "sim" / "index.html")
