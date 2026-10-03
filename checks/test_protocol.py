"""Protocol load suite: the live file passes; a file that deletes or weakens a RED rule is refused."""
from pathlib import Path

import pytest
import yaml

from app.engine import Protocol, ProtocolRejected

ROOT = Path(__file__).resolve().parent.parent
LIVE = ROOT / "config" / "protocol.yaml"


def _variant(tmp_path, edit):
    cfg = yaml.safe_load(LIVE.read_text(encoding="utf-8"))
    edit(cfg)
    p = tmp_path / "protocol.yaml"
    p.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return p


def test_live_file_loads():
    Protocol.load(LIVE)


def test_deleting_a_red_rule_is_refused(tmp_path):
    p = _variant(tmp_path, lambda c: c.update(rules=[r for r in c["rules"] if r["id"] != "R5"]))
    with pytest.raises(ProtocolRejected, match="T5"):
        Protocol.load(p)


def test_parameter_outside_allowed_is_refused(tmp_path):
    p = _variant(tmp_path, lambda c: c["parameters"]["cough_red_days"].update(value=30))
    with pytest.raises(ProtocolRejected, match="not in allowed"):
        Protocol.load(p)


def test_non_red_output_is_refused(tmp_path):
    def edit(c):
        c["rules"][0]["then"] = "HOME_CARE"
    with pytest.raises(ProtocolRejected, match="RED only"):
        Protocol.load(_variant(tmp_path, edit))


def test_cough_threshold_21_still_passes(tmp_path):
    Protocol.load(_variant(tmp_path, lambda c: c["parameters"]["cough_red_days"].update(value=21)))
