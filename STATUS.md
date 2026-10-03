# STATUS

**Updated:** Sat 3 Oct, ~15:15 ET · **Block:** after `results`: diagnosis done, v3 NO-GO (pending Florian), writing · **Last tag:** `results` (ab79b5b)

## Seal record (GitHub push record is the evidence)
| Item | Commit | Time (ET) | Notes |
|---|---|---|---|
| Generation prompts + card sampler | 3cec268 | 12:21 | before any generation call |
| Set (b) | f76c92d | 12:22 | 25 rows, claude-opus-5-5, unopened |
| Y-test | 839a4a5 | 12:24 | 150 rows, claude-opus-5-5, 80/55/15, unopened |
| Y-dev | d870e2a | 12:24 | 120, gpt-5.5 |
| X train | d15098a | | 1,200, gpt-5.5 (1,195 after dedupe) |
| v2 augmentation prompt | c775d8e | 13:46 | before the v2 generation call |
| v2 augmentation data | prep_v2 commit | | 474 gpt-5.5, 462 kept (1 near a CG/T probe, 0 Y-dev, 11 duplicates removed) |

## Tags
`slice-chw` 92d90b5 · `slice` 5a54bff · `mvs` ec66996 · `freeze` not yet (held)

## Live state (Pi, florian@192.168.1.208:8000)
- Door ON (T1-T35, CG1-CG18 and both lints pass on every load). Live keyword list: **E2** (k = 4; passes T and CG with E2 loaded).
- Encoder **not live** on the parent line (rung 3): CG1/CG5/CG5b/CG10/CG18 red with the v1 encoder on; the Y-dev gate fails on needless go-nows. The service applies this automatically on every load.
- Door-off fail-safe: fixed CG_GO_NOW_U + CHA ALERT copy (never silent).
- **Board model ON** (v2 trim + weight-only INT8, calibrated): board lines only ("model: possible {sign}, check" / "model unsure: please read"), sort danger > possible > unsure > rest. Parent reply unchanged (tested with the model on and off; CG1-CG18 with the model on). Temperatures (X-val) 0.25-0.65; lo = 0.068, hi = 0.9904 (Y-dev): 30.8% of Y-dev to "please read", 0 danger below lo, 0 no-danger "possible". Model hash in config/board_model.json.

## Models (Y-dev: missed of 60 danger / needless of 45 no-danger)
| Model | Role | Y-dev | Notes |
|---|---|---|---|
| v1 FP32 | registered row (prereg section 7) | 4/60, 6/45 | the registered INT8 fails section 7 (87/120, 30 danger missed) |
| v1 trim (9,759 tokens) + weight-only INT8 | deployed row | 4/60, 6/45 | 90.3 MB with tokenizer; 120/120 agreement; 322 MB RSS; p95 86 ms (4 cores), 118 (2), 216 (1) |
| v2 FP32 (one run, + 462 terse/denial messages) | own labelled row | 3/60, 5/45 | fails CG5/CG5b/CG10/CG12 and the Y-dev gate; v2 deployed agrees 119/120 |
| Keyword list E2 | comparator, live | 10/60, 2/45 | |
| Keyword list v0 | | 30/60, 3/45 | |

## Quantization sweep (Pi, ONNX Runtime; Y-dev agreement with v1 FP32)
| Variant | Size MB (+tok) | Peak RAM MB | p95 ms 4c / 1c | Agree | Danger missed | Passes |
|---|---|---|---|---|---|---|
| FP32 | 1,074.9 | 1,851 | 126 / 373 | 120/120 | 0 | yes |
| INT8 MatMul (registered INT8) | 832.1 | 1,610 | 44 / 117 | 87/120 | 30 | no |
| INT8 MatMul per-channel | 832.5 | 1,611 | 46 / 120 | 113/120 | 7 | no |
| INT8 incl. embeddings | 281.6 | 625 | 46 / 117 | 89/120 | 29 | no |
| Weight-only INT8 | 283.1 | 1,432 | 182 / 317 | 120/120 | 0 | yes |
| Trim FP32 | 355.4 | 490 | 158 / 365 | 120/120 | 0 | yes |
| Trim + INT8 MatMul | 112.6 | 252 | 46 / 117 | 87/120 | 30 | no |
| Trim + INT8 incl. embeddings | 90.0 | 228 | 46 / 118 | 90/120 | 28 | no |
| **Trim + weight-only INT8 (deployed)** | **90.3** | **322** | **86 / 216** | **120/120** | **0** | **yes** |

INT4 not built (export failed on the first try). CPU clock not reduced (cpufreq needs root).

## Done since `mvs`
B6; B7 (v1, 0.4 min); B10 (export, sweep, Pi bench); B11 (harness, E2 mining, Y-dev table); B13 up to the gate. Also:
- case board, phone-style CHW pane and follow-up reminders (followup_days 3, S1 pp.98/116 verified in the PDF);
- door-off fail-safe;
- real Busia facilities (OSM/HDX, ODbL) in the registry;
- DATA.md (verified evidence file only);
- README: CHW framing, eCHIS, county box, Responsible AI with the DPA line, where the record lands, sweep table, on-device card, changes after prereg;
- B16 metric code (CP, McNemar), run on Y-dev only and pushed;
- privacy must-stay tests (no name; retention purge, retention_days 30);
- MASSIVE exploratory script, freeze record and test-run scripts (none run).

Bug fixed: "18m ..." inside an open case was read as options 1 and 8.

## Since freeze
- `freeze` 28609b6 (14:06:09 ET); sealed raw outputs 357f63a; `results` ab79b5b (14:31). Outcome: no native set; safety switch fired on (b) and Y-test; statements verbatim in README/results.
- Final parent strings live (Swahili first + English; CG_TOLD in the parent's language, waiting time in minutes). CLAUDE.md rule 8 updated by Florian (1bd2335).
- P4 phone page live at http://192.168.1.208:8000/phone. Florian's iPhone (Safari, iOS 18.7, UA "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.7.5 Mobile/15E148 Safari/604.1"): 50 Y-dev p50 109 ms, p95 170 ms, load 1.28 s; parity 20/20 tokens, flags, bands, max dp 0.021; offline in airplane mode worked. No reload offline (no HTTPS service worker).
- Pi pinned to 1 core: full service p50 397 / p95 516 ms per parent message, peak RSS 549 MB. The 2 GB cap was not enforced (user cgroup has no memory controller).
- Diagnosis D1-D5 done (see README Results and results/d5_everyday_swahili.json). Fresh test set y_test2 sealed unopened (64a4fff).

## v3 (after results, exploratory)
- Criteria efdeab3 + 07323eb; data db7cad9; configs before evaluation 5faab32; evaluation 17df7ec^ (v3/evaluation.json). v3 passes (a)(b)(c); re-tuned v2 fails (c). Board = v3 (config/board_model.json; v2 kept as board_model_v2_shipped.json).
- STEP 5 on the Pi, shipped v3 board file (models/onnx/v3_trim_wq8, 92.7 MB, git hash-object 4c7916c9): model only p95 80 ms (4 cores) / 215 ms (1 core) at 64 tokens, peak RSS 350 MB; full round trip on 1 core p95 530 ms (p50 404), whole service peak RSS 569 MB (includes the v1 encoder loaded for the CG check and the web simulator). Memory cgroup disabled at boot (cgroup_disable=memory): no cap possible without a boot-config change. Phone page serves v3: parity 20/20 tokens, flags, bands (max dp 0.021); iPhone re-run with the v3 file (Safari, same UA as P4, received 16:04:53): 50 Y-dev p50 110 ms, p95 165 ms, download 3.2 s, load 1.26 s.

## Open issues
- `freeze` held until the planner's go. Then: freeze record -> push tag -> run tests (a), (b) and Y-test with E2 / registered v1 FP32 / deployed / v2 rows, and MASSIVE; counts only.
- 60 s three-actor clip: Florian to record.
- Entry-level phone spec line on the on-device card: waiting for the verified spec (placeholder in README).

## Next
On the go:
0. FREEZE.md must also record the board model (config/board_model.json: hash, temperatures, lo, hi).
1. `train/freeze_record.py models/onnx/fp32 models/onnx/trim10k_wq8`, then commit FREEZE.md, tag `freeze` and push.
2. `train/run_tests.py` (+ v2 arm), `train/massive_row.py` and `train/board_row.py` on the Pi.
3. Sleep, then the B16 tables.

## Live demo build (Sat 3 Oct, ~16:15 ET)
- Public mode committed (84773a0). Drafts for review: hf/model_card.md, space/README.md (199517f). Nothing pushed to HF.
- Clean clone of main + `pip install -r requirements-demo.txt` (Python 3.11): service starts without the model (board model absent), door on, Swahili convulsions message goes to GO NOW with alerts.
- Local docker build of space/Dockerfile with TAG=main (the `submission` tag doesn't exist yet) and the v3 files mounted: SHA-256 ok for both files, public: true, door on, banner shown, board shows the v3 band, /phone 200, /admin/reload and /phone/parity 404, a 1,001-char body gets 413, /demo/reset 200.
- Pending: iPhone parity tap (Florian); "Try it in 60 seconds" section; `submission` tag; HF push only after Florian's OK.
