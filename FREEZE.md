# Freeze record

Written by `train/freeze_record.py` for the `freeze` commit. No test set was opened.

## Sealed sets (commit, git insertion count at the seal commit)

| Set | File | Commit | Lines |
|---|---|---|---|
| (a) | `tests/caregiver_set_a.csv` | b49214293144da61c9229a4c8596072c7178411f | 26 |
| (b) | `tests/caregiver_set_b.csv` | f76c92dc6abe7c7405937cba2ed26e0e67f34720 | 26 |
| Y-test | `tests/y_test.jsonl` | 839a4a5c019c02330587aa23d31ee659b221a026 | 150 |
| Native | none | none (no native set) | 0 |

## Keyword list

- E2 (comparator): T-list rows + mined n-grams, `config/e2.json`, k = 4 (search {'0': 0, '1': 0, '2': 0, '3': 0, '4': 0, '5': 1}).
- Live keyword list: E2 (passed T1-T35 and CG1-CG18 with E2 loaded).

## Models

- Registered model (prereg section 7): FP32 ONNX, `models\onnx\fp32`, git hash-object `8ebe55dea306eec3fd40daefd7dd3a6084c95b31`.
- Deployed variant (deployment rule, Y-dev): `models\onnx\trim10k_wq8` (Vocab trim + INT8 weight-only (per-channel)), 89.7 MB + tokenizer 0.6 MB, git hash-object `8b46d5227d204a457013349e161d8e2aa818ea6f`.
- v2 (own labelled row; one extra run on X train + 462 terse/denial messages): FP32 `models/onnx/v2_fp32`, git hash-object `879009a138df8abb10fe386840739e96939a4459`; board model `models/onnx/v2_trim_wq8`, git hash-object `e8e8883382b74bd165ab3eb075a01dca96dd92d5`.
- Base model: Davlan/afro-xlmr-base; generators: X train, v2 augmentation and Y-dev gpt-5.5; tests claude-opus-5-5.
- Model weights stay out of git.

## Board model (board only; never the parent reply)

```
{
 "model_dir": "models/onnx/v2_trim_wq8",
 "model_hash": "e8e8883382b74bd165ab3eb075a01dca96dd92d5",
 "temperatures": {
  "convulsions": 0.6,
  "not_drink_feed": 0.25,
  "vomits_everything": 0.35,
  "sleepy_unconscious": 0.6,
  "blood_stool": 0.65,
  "cough_long": 0.4,
  "diarrhoea_long": 0.5,
  "fever_long": 0.6
 },
 "lo": 0.068065,
 "hi": 0.9,
 "fit_on": "X-val (165 messages, held out from x_train_v2.jsonl with seed 42)",
 "thresholds_on": "Y-dev (gpt-5.5, 120)",
 "note": "lo = lowest Y-dev danger score; with 60 danger messages this bounds the miss rate at roughly 1/61 on data like Y-dev. hi = highest Y-dev no-danger score.",
 "hi_data_driven": 0.990449,
 "hi_decision": "Board threshold hi = 0.9 (chosen on Y-dev before the freeze, Sat 3 Oct). At hi = 0.9904, no Y-dev no-danger message was marked 'possible', but 30.8% of messages went to 'please read' and 'possible' almost never fired. At hi = 0.9, review load falls to 12.5%, at the cost of 2 of 45 Y-dev no-danger messages marked 'possible'. On the board a false 'possible' only moves a case up the health worker's list: no SMS is sent and no case status changes. A review load of about a third of all messages risks the health worker ignoring the flags (mTrac's on-time volunteer reporting fell from 60% to 9%; DFID 2014 via SDSN TReNDS 2018). lo = 0.068 is unchanged, so no Y-dev danger message falls below it. The full sweep is in the table above."
}
```

## Go-live gate on Y-dev (prereg section 9)

```
{
 "encoder_misses_le_keyword": true,
 "encoder_needless_le_keyword": false,
 "shared_path_complete": true,
 "p95_ms_per_message": 40.1,
 "p95_budget_ms": 300,
 "p95_in_budget": true,
 "passes": false
}
```

## Live parent line

- Encoder live on the parent line: no. v1: CG1/CG5/CG5b/CG10/CG18 red with the encoder on and the Y-dev gate fails (needless 6/45 vs E2 2/45). v2: CG5/CG5b/CG10/CG12 red and the Y-dev gate fails (needless 5/45 vs 2/45).
- Rung 3 (approved wording): "The parent line runs the keyword list live; the model was scored on the Pi (single pass, frozen), not used live, because it failed the caregiver safety tests."
- Door on: T1-T35, CG1-CG18 and both lints pass on every load.

## Test runs after this push

Sets (a), (b), Y-test, rows: E2 (comparator) / registered v1 FP32 / deployed v1 / v2; then MASSIVE sw-KE (exploratory); then the board row (exploratory). Raw files only; metric code was pushed before (d3dd0e9).
