# STATUS

**Updated:** Sat 3 Oct · **Block:** B3 done (local), next B4 · **Last tag:** `prereg`

## Seal record (commit times are push times from the local clock; GitHub push record is the evidence)
| Item | Commit | Time (ET) | Notes |
|---|---|---|---|
| Build-agent rules | f902ff3 | before 12:00 | pre-event, not project code |
| Generation prompts + card sampler | 3cec268 | 12:21 | `prompts/caregiver_system.txt`, `gen/cards.py`, `gen/generate.py`; before any generation call |
| Set (b) | f76c92d | 12:22 | `tests/caregiver_set_b.csv`, 25 rows written (26 lines incl. header), 0 errors, claude-opus-5-5, unopened |
| Y-test | 839a4a5 | 12:24 | `tests/y_test.jsonl`, 150 of 150 written, 0 errors, claude-opus-5-5, 80/55/15, unopened |
| Y-dev | d870e2a | 12:24 | `data/y_dev.jsonl`, 120 of 120, gpt-5.5 |
| X train | d15098a | | `data/x_train.jsonl`, 1,200 of 1,200, gpt-5.5 (525 SW / 382 EN / 293 mixed) |

## Done (local, desktop)
- SIM ae014a6: 3-pane simulator at `/`, corner label, `?clean=1` hides message IDs.
- B3: `config/protocol.yaml` (fields with `observer`, RED rules R1-R11, parameters with allowed values), `app/engine.py` (E1, Z0, O1, O3, O4, O2, F1, F3), `app/must_stay_red.py` T1-T21 + FX1 (forced extractor exception) + FX2 (no text read ABSENT): all pass. `python -m app.check`; `pytest checks` (deleting R5 is refused). `/admin/reload` keeps the last valid file on rejection; no valid file = SERVICE_DOWN.
- B2 code in repo: `app/server.py` (POST /sms {from,to,body}, GET /outbox), SQLite outbox, `config/registry.yaml` (pre-seeded, synthetic numbers). Local round trip 0.27 s. Not yet on the Pi (SSH blocker).

## Notes
- SEAL0 not used (the 30 parent cards don't exist); card dedupe skipped.
- Set (b) label_line format: "{id} danger|no danger: {sign|none}"; labels from the grid ID.

## Open issues
- **Pi SSH:** `FloFlo@192.168.1.208` (and floflo/pi/flo/florian) refuse the desktop key (publickey,password). B2 deploy needs Florian to add `~/.ssh/id_ed25519.pub` to the Pi's `authorized_keys`, or confirm the username.

## Next
B2: generic `{from, to, body}` endpoint + outbox + pre-seeded registry; built and tested locally, deployed to the Pi once SSH works.
