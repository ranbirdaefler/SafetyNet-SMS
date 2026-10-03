# v3 criteria (committed before any v3 data generation or training, Sat 3 Oct 2026)

Exploratory, after `results`. The parent line stays on the keyword list E2 whatever happens here. v3 can only replace v2 on the health worker's case board. Everything below is reported as "after results, exploratory".

## Splits: each used for one purpose only

| Purpose | Data |
|---|---|
| **TRAIN** | X train (deduped, 1,195) + the v2 additions (462) + new gpt-5.5 data (denial contrast pairs incl. extra "very sleepy" denials; duration hard negatives under the cut-offs) + MASSIVE 1.1 sw-KE **train** + AfriSenti swa **train**, as no-danger, after dropping sentences that mention health, illness or children + code-generated SMS-noise copies of training messages |
| **THRESHOLDS** (board lo/hi; go-now stays at p >= 0.5) | Y-dev (gpt-5.5, 120) + MASSIVE sw-KE **dev** (validation, 2,033) + FLORES-200 swh_Latn **dev** (997) + AfriSenti swa **dev** (453). FLORES has no train split and is never used for training |
| **EVALUATION** | sealed y_test2 (claude-opus-5-5, 150, sealed unopened in 64a4fff before this file) + MASSIVE sw-KE **test** (the same 1,000, seed 20261003) + FLORES-200 swh_Latn **devtest** (1,012) + AfriSenti swa **test** (748) |
| **Vocabulary keep-list** (shipped variant) | TRAIN splits only |
| **Calibration** (per-head temperatures) | the 10% X-val split held out from TRAIN by train.py (seed 42) |

No evaluation split is opened before the single joint v2/v3 evaluation. Raw third-party text (MASSIVE, FLORES, AfriSenti) stays local and gitignored.

## Fixed now

- **Recipe:** the registered one (BCE, no class weights, lr 3e-5, bf16, 3 epochs, max length 256, batch 16, seed 42, AdamW, linear decay, 10% X-val). One run.
- **SMS noise:** typos (one swapped or dropped letter in a word), shorthand (mtoto -> mtt, homa -> hm, sana -> sn), missing spaces between two words, lowercasing. Never applied to a denial word (hana, hajapata, hakuna, bila, wala, si, sio, no, not, never, without, isn't, doesn't, didn't, hasn't, don't and their apostrophe-less forms) or to any word of a danger term (T-list, shared stage, C4) or a number. Labels unchanged.
- **Human-written Swahili filter:** drop a sentence if it contains any of: mtoto, watoto, mtt, child, baby, mgonjwa, ugonjwa, kuumwa, anaumwa, homa, kikohozi, kuhara, damu, hospitali, daktari, dawa, sick, ill, fever, cough, doctor, hospital, medicine, health, afya, kifo, death.

## Board thresholds for v3 (rule written before training)

Score = the calibrated max danger-head probability. Flagged = "possible" or "unsure".
1. **lo:** the highest value that keeps **0** Y-dev danger messages below it (= the lowest Y-dev danger score).
2. **hi:** the smallest value at which at most 2 of 45 Y-dev no-danger messages are "possible" and at most 5% of each threshold-split everyday source is "possible".
3. **Flag cap:** with lo from step 1, the share flagged on each threshold-split everyday source (MASSIVE dev, FLORES dev, AfriSenti dev) should be <= 35%.
4. **If 1 and 3 cannot both hold:** safety gives way last. lo stays at the value from step 1 (no Y-dev danger message below it); lo is **not** raised to meet the flag cap. The excess is reported, and criterion (c) below then decides.

v2 is evaluated at its **frozen** thresholds (lo 0.068, hi 0.9), as shipped.

## v3 replaces v2 on the board only if ALL of

- **(a)** T1-T35 and CG1-CG18 are green with the v3 board model on.
- **(b)** On y_test2, keywords + v3 board miss no more danger messages than keywords + v2 board. A danger message counts as missed by "keywords + board" when E2 does not trigger go-now AND the board shows no flag.
- **(c)** The v3 board flags <= 35% of each everyday-Swahili EVALUATION split (MASSIVE test 1,000, FLORES devtest, AfriSenti test).

## Shipped variant

Whichever model ends up on the board ships with a vocabulary re-trimmed from the TRAIN splits (incl. the human-written Swahili) and 8-bit weights. It must agree with its full-size version on >= 99% of go-now decisions and miss no Y-dev danger message on Y-dev, AND agree on >= 99% of board flags on each threshold split.

## Research rows (reported, not required)

- v3 alone vs keywords on y_test2: danger missed, needless trips.
- False alarms (triggered, parent-line rule) on each everyday-Swahili test split for keywords, v2 and v3.

## Regex (labelled post-hoc, Sat 3 Oct)

"1yr 1 month" (a years count directly followed by a months count, no "and"/"na" between) is read as one age (13 months). "3 y and 1 m" stays two ages and the younger decides. "5 days" read as an age stays a known gap. The tagged `results` stay as computed; the y_test2 run uses the fixed regex for both arms.

## Hard stop

If v3 is not evaluated by 19:00 ET, it is dropped and reported.
