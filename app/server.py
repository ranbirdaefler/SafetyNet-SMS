"""One generic inbound endpoint: POST /sms {from, to, body}. The role comes from `to`.

SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway; a gateway adapter
is a thin mapping onto this endpoint and is not built.
"""
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.registry import Registry
from app.store import Store
from app import service

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = Registry(os.environ.get("SNS_REGISTRY", ROOT / "config" / "registry.yaml"))
STORE = Store(os.environ.get("SNS_DB", ROOT / "data" / "sms.db"))

app = FastAPI(title="SafetyNet-SMS")


class Inbound(BaseModel):
    sender: str = Field(alias="from")
    to: str
    body: str


@app.post("/sms")
def sms(msg: Inbound):
    role = REGISTRY.role(msg.to)
    before = STORE.last_outbox_id()
    STORE.log_in(msg.sender, msg.to, role, msg.body)
    if role is not None:
        service.handle(STORE, REGISTRY, role, msg.sender, msg.body)
    return {"role": role, "replies": STORE.outbox_since(before)}


@app.get("/outbox")
def outbox(since: int = 0):
    return STORE.outbox_since(since)


@app.get("/inbox")
def inbox(since: int = 0):
    return STORE.inbox_since(since)


@app.get("/config")
def config():
    r = REGISTRY
    return {"lines": r.lines, "parents": list(r.parents), "chps": [c["phone"] for c in r.chps.values()],
            "facility": r.facility["phone"], "cha": [c["phone"] for c in r.cha.values()]}


@app.get("/")
def simulator():
    return FileResponse(ROOT / "sim" / "index.html")
