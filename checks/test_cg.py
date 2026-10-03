from app import cg_tests
from app.engine import Protocol


def test_cg1_to_cg18_and_lints_pass():
    assert cg_tests.run(Protocol.load("config/protocol.yaml")) == []
