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
from app import cg_tests, lexicon
from app.door import keyword_extractor
lexicon.use(lexicon.e2_list())
e2_ok = not must_stay_red.run(proto) and not cg_tests.run(proto)
print("E2 (k=%s) with T1-T35 and CG1-CG18: %s" % (lexicon.LIVE["k"], "PASS, E2 live" if e2_ok else "FAIL, v0 stays live"))
if not e2_ok:
    lexicon.use({"name": "v0", "rows": lexicon.T_LIST, "k": lexicon.V0_K})
variants = [(lexicon.LIVE["name"] + ", encoder off", (keyword_extractor,))]
model = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "models" / "onnx" / "trim10k_wq8")
if Path(model, "model.onnx").exists():
    from app.encoder import Encoder
    variants.append((lexicon.LIVE["name"] + ", encoder on", (Encoder(model), keyword_extractor)))
cg_failed = cg_tests.run(proto, verbose=True, variants=variants)
print("DOOR OFF: " + ", ".join(cg_failed) if cg_failed else "DOOR ON: CG1-CG18 and lints pass")
sys.exit(2 if cg_failed else 0)
