# STATUS

**Updated:** Sat 3 Oct, 12:25 ET · **Block:** B1 (generation running), then B2 · **Last tag:** `prereg`

## Seal record (commit times are push times from the local clock; GitHub push record is the evidence)
| Item | Commit | Time (ET) | Notes |
|---|---|---|---|
| Build-agent rules | f902ff3 | before 12:00 | pre-event, not project code |
| Generation prompts + card sampler | 3cec268 | 12:21 | `prompts/caregiver_system.txt`, `gen/cards.py`, `gen/generate.py`; before any generation call |
| Set (b) | f76c92d | 12:22 | `tests/caregiver_set_b.csv`, 25 rows written (26 lines incl. header), 0 errors, claude-opus-5-5, unopened |
| Y-test | 839a4a5 | 12:24 | `tests/y_test.jsonl`, 150 of 150 written, 0 errors, claude-opus-5-5, 80/55/15, unopened |
| Y-dev | (this commit) | | `data/y_dev.jsonl`, 120 of 120, gpt-5.5 |

## Running
- X train (gpt-5.5, 1,200 cards): background, log in `logs/`.
- B2 code in repo: `app/server.py` (POST /sms {from,to,body}, GET /outbox), SQLite outbox, `config/registry.yaml` (pre-seeded, synthetic numbers). Local round trip 0.27 s. Not yet on the Pi (SSH blocker).

## Notes
- SEAL0 not used (the 30 parent cards don't exist); card dedupe skipped.
- Set (b) label_line format: "{id} danger|no danger: {sign|none}"; labels from the grid ID.

## Open issues
- **Pi SSH:** `FloFlo@192.168.1.208` (and floflo/pi/flo/florian) refuse the desktop key (publickey,password). B2 deploy needs Florian to add `~/.ssh/id_ed25519.pub` to the Pi's `authorized_keys`, or confirm the username.

## Next
B2: generic `{from, to, body}` endpoint + outbox + pre-seeded registry; built and tested locally, deployed to the Pi once SSH works.
