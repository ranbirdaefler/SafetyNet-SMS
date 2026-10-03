---
license: other
license_name: research-and-evaluation-only
language:
- sw
- en
base_model: Davlan/afro-xlmr-base
library_name: onnx
tags:
- text-classification
- swahili
- health
- synthetic-data
---

# SafetyNet-SMS board model (v3)

**Not for clinical use.** A hackathon prototype, trained and tested on AI-written messages. It has never seen a real parent's text.

## What it does

Reads a parent's SMS about a sick child (Swahili, English or mixed) and gives the community health worker's board a band per danger sign: *possible*, *unsure* or *none*. It **only annotates the health worker's board**. It never decides or changes what a parent is told: the parent line runs on a fixed keyword list and rules, and parents receive only fixed, pre-approved messages.

## Files

| File | Size | SHA-256 |
|---|---|---|
| `model.onnx` (vocabulary-trimmed, 8-bit weights, per-channel) | 92.7 MB | `0dcaaf1353e76556680f352d13c0de8571a2878394b6ac1ddb9d9b46e933b0e6` |
| `tokenizer.json` | 0.77 MB (766,645 bytes) | `7146c767e3087e96aa375c590c239a9210172393856eecdc4c0d52a34d398a6b` |

Board thresholds (from `config/board_model.json` in the GitHub repo): lo 0.849, hi 0.997, per-head temperatures fitted on v3's held-out X-val (547 messages).

## Base model

Fine-tuned from AfroXLMR-base (Alabi et al., COLING 2022), MIT licence.

## Training data

- Synthetic messages written by GPT (`gpt-5.5`): training set and Y-dev (threshold set). Test sets were written by a different model family (Claude, `claude-opus-5-5`).
- Human-written Swahili with no health content, used as no-danger examples:
  - MASSIVE 1.1 sw-KE train (CC BY 4.0), 1,000 utterances after a health filter.
  - AfriSenti swa train (dataset card CC BY 4.0; the paper restricts commercial and state-actor use without the creators' approval). **v3 includes AfriSenti training data; a ministry deployment would retrain without it or seek the creators' approval.**
- Thresholds only (never trained on): MASSIVE sw-KE validation, FLORES-200 swh_Latn dev (CC BY-SA 4.0), AfriSenti swa dev, Y-dev.

## Results (after results, exploratory; one joint evaluation)

| Evaluation split (never used for training or thresholds) | Keywords + v2 board (as shipped) | Keywords + v3 board |
|---|---|---|
| Fresh test set y_test2 (Claude-written, 80 danger): danger missed | 2 | 2 |
| y_test2 (55 no-danger): flagged by the board | 18 | 2 |
| Everyday Swahili, MASSIVE test (1,000): flagged | 62.6% | 0.0% |
| Everyday Swahili, FLORES-200 devtest (1,012): flagged | 70.6% | 0.1% |
| Everyday Swahili, AfriSenti test (748 tweets): flagged | 80.5% | 0.0% |

Caregiver tests (must-stay-RED T1–T35, CG1–CG18) pass with v3 running on the board; the parent line doesn't use the model.

## Known failures

- On the fresh set, keywords + v3 board miss 2 danger messages, both long-duration signs in Swahili (fever, diarrhoea). On the three earlier sealed sets (report-only), keywords + v3 board miss one danger message on each: a "cannot drink or feed" in negative form (mixed Swahili/English) and two long-duration diarrhoea messages in Swahili.
- On the three earlier sets, keywords + v3 board let 3 of 104 danger messages through that keywords + v2 board caught (the v2 board caught all three older-set misses); v2's board, however, flagged 62.6-80.5% of everyday Swahili.
- All test data is AI-written. Thresholds must be re-set on real parents' texts before any use.
- Swahili is the only local language tested. Kikuyu and Luo are not covered.

## Disclosure

v3's training changes were chosen after seeing error types on dev data and, report-only, on earlier test sets; v3 was evaluated once on a fresh sealed set. The fresh set includes the error types v3 was trained to fix (denials, durations).

## Licence

Licence: other. The base model, AfroXLMR-base, is MIT-licensed. The MASSIVE training data is CC BY 4.0 (attribution: Amazon MASSIVE 1.1). AfriSenti's paper restricts commercial and state-actor use without the creators' approval, so these weights are released for research and evaluation only.

## Device

Runs offline in a phone browser (iPhone, Safari, onnxruntime-web, single thread: p95 165 ms; a best case). Raspberry Pi 5 limited to 1 core: p95 215 ms. Not yet measured on an entry-level Android.
