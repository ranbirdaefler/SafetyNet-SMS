"""Load the protocol file and print the must-stay-RED results: python -m app.check [protocol.yaml]"""
import sys
from pathlib import Path

from app import must_stay_red
from app.engine import Protocol, ProtocolRejected

ROOT = Path(__file__).resolve().parent.parent
path = sys.argv[1] if len(sys.argv) > 1 else ROOT / "config" / "protocol.yaml"
try:
    proto = Protocol.load(path, run_suite=False)
except ProtocolRejected as e:
    sys.exit(f"REJECTED (schema): {e}")
failed = must_stay_red.run(proto, verbose=True)
print("REJECTED: " + ", ".join(failed) if failed else "LOADED: all must-stay-RED tests pass")
if failed:
    sys.exit(1)
from app import cg_tests
cg_failed = cg_tests.run(proto, verbose=True)
print("DOOR OFF: " + ", ".join(cg_failed) if cg_failed else "DOOR ON: CG1-CG18 and lints pass")
sys.exit(2 if cg_failed else 0)
