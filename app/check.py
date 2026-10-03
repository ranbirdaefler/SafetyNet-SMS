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
lexicon.use(lexicon.live_list(lexicon.e2_list()))
e2_ok = not must_stay_red.run(proto) and not cg_tests.run(proto)
print("E2 (k=%s) with T1-T35 and CG1-CG18: %s" % (lexicon.LIVE["k"], "PASS, E2 live" if e2_ok else "FAIL, v0 stays live"))
if not e2_ok:
    lexicon.use(lexicon.live_list({"name": "v0", "rows": lexicon.T_LIST, "k": lexicon.V0_K}))
model = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "models" / "onnx" / "trim10k_wq8")
if Path(model, "model.onnx").exists():
    from app.encoder import Encoder
    enc_failed = cg_tests.run(proto, variants=[(lexicon.LIVE["name"] + ", encoder on", (Encoder(model), keyword_extractor))])
    print("ENCODER LIVE: CG1-CG18 pass with it on" if not enc_failed else
          "ENCODER NOT LIVE (rung 3, keyword list runs the parent line): " + ", ".join(enc_failed))
cg_failed = cg_tests.run(proto, verbose=True, variants=[(lexicon.LIVE["name"] + ", encoder off", (keyword_extractor,))])
print("DOOR OFF: " + ", ".join(cg_failed) if cg_failed else "DOOR ON: CG1-CG18 and lints pass")
sys.exit(2 if cg_failed else 0)
