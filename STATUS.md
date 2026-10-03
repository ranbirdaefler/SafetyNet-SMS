# STATUS

**Updated:** Sat 3 Oct · **Block:** D1 done, `slice` tagged; next B9 (CHW rest) · **Last tag:** `slice`

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

- **B2 live on the Pi** (florian@192.168.1.208, `sh scripts/pi_run.sh`, port 8000): desktop -> Pi HELP round trip 39-63 ms (3 curl runs); unregistered CHP number -> UNREGISTERED; simulator at http://192.168.1.208:8000/ round trip checked in the desktop browser. Must-stay-RED suite passes on the Pi.

- B4 717125f: CHP sessions, shared age/duration/MUAC regex (word lists in `app/textparse.py` docstring), keyword list v0 typed verbatim (`app/lexicon.py`), shared stage + C4 lists, full ASK_SIGNS (394 chars, 3 segments), numbered parser, REFER_NOW. Text T-tests T13/T15/T16/T18/T20/T22/T23/T25-T29/T35 pass; 54 pytest checks pass.
- B5 1938809: ALERT to facility + CHA (written before REFER_NOW), facility code -> ARRIVED (CHP + CHA) then ACK; unknown code or unregistered sender gets nothing.
- `slice-chw`: run over the Pi simulator in the browser (18m homa siku 3 -> ASK_SIGNS -> "7873 5" -> ALERT x2 + REFER_NOW -> facility "7873" -> ARRIVED + ACK). Pi clock America/New_York.

- D1 abfd316: parent door. `app/door.py` `parent_policy()` (the one function live + harness call, F5): v0 caregiver rows + duration regex + shared stage (ignores cues; chest -> "breathing complaint") + C4 + under 2 m; C9 scope order. Paths D1/D2 (unregistered), D3, D4 (CHP_CALL + full ASK_SIGNS, then CG_TOLD), D5 (no age), D6, D7, D8, D13-D15, D16/D17 link, D23. Send-time guard: a parent SMS must match one of the 5 templates. 61 pytest checks pass.
- `slice`: run on the Pi simulator in the browser (parent text -> CG_TOLD + CHP_CALL + ASK_SIGNS -> CHP "4006 5" -> ALERT x2 + REFER_NOW + CG_GO_NOW -> facility "4006" -> ARRIVED + ACK); parent "degedege" -> ALERT x2 + CHP_GO_NOW + CG_GO_NOW checked by curl on the Pi.

## Open issues
- Wording to confirm (planner/Florian): D7 (no CHP assigned) sends CG_GO_NOW, whose fixed text says "Your health worker has been told" although no CHP exists (the CHA is told). ALERT for a parent with no CHP reads "CHU -, CHP -".

## Next
B9: CHW rest (A1 24 h digit window, A3-A5, timers, M4, NON_RED, option 8), T22-T35 -> then D2a (timeouts, C2, C4, scope, X6, F2), D2b (CG1-CG18, lints).
