# Results

Pre-registered claim (native Swahili): NOT TESTED

Tabulated once, on the sealed outputs as committed in 357f63a (freeze 28609b6). Metric code pushed before: d3dd0e9 (tables), 1d1d799 (language rows), 7b9fb58 (board rows).

## Outcome (pre-registered, checked in order: safety switch, then Win, then Tie-or-loss; no native set)

Safety switch (C11): fired on (b), (ytest).

> No native speaker's texts were sealed in time, so my registered claim is not tested. On three stand-in sets, the model sent 10 of 12 children with a danger sign to the clinic in 25 test messages an AI model wrote from a fixed case grid, 9 of 12 in 25 AI-written Swahili texts no native speaker checked, and 65 of 80 in 150 AI-written test texts; the keyword list 8, 10, 66. Needless trips: model 4 of 13, 0 of 13, 3 of 55; keyword list 3, 3, 11. None are real parents' texts, so the model is not shown to beat a keyword list.

On screen with it: "Test messages written by an AI model from a fixed case grid; no native or human-written test set."

> Before testing I set a rule that the model may not miss more children with a danger sign than a keyword list; on (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker it missed 3 of 12, the keyword list 2, so the keyword list now runs the parent line.

> Before testing I set a rule that the model may not miss more children with a danger sign than a keyword list; on Y-test, Claude, caregiver it missed 15 of 80, the keyword list 14, so the keyword list now runs the parent line.

### (a) Claude-written from a fixed case grid (pre-registered row)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = FP32 ONNX on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/12 | 13/13 | | | | |
| never go now | 12/12 | 0/13 | | | | |
| keyword list (E2) | 4/12 (9.9-65.1%) | 3/13 (5.0-53.8%) | 0/0 | 0 | 3 |  |
| ours (registered v1 FP32) | 2/12 (2.1-48.4%) | 4/13 (9.1-61.4%) | 0/0 | 0 | 2 | 126.0 ms |

Discordant no-danger messages: b (keyword list only) = 0, c (ours only) = 1; exact McNemar p = 1.0.


Error listing:

| Arm | Message ID | Error | Class |
|---|---|---|---|
| keyword list (E2) | D02 | missed go-now | hedging, lay wording |
| keyword list (E2) | D04 | missed go-now | negation |
| keyword list (E2) | D05 | missed go-now | plain |
| keyword list (E2) | D09 | missed go-now | split |
| keyword list (E2) | N03 | needless go-now | negation |
| keyword list (E2) | N11 | needless go-now | plain |
| keyword list (E2) | N13 | needless go-now | plain |
| ours | D01 | missed go-now | plain |
| ours | D02 | missed go-now | hedging, lay wording |
| ours | N02 | needless go-now | negation |
| ours | N03 | needless go-now | negation |
| ours | N11 | needless go-now | plain |
| ours | N13 | needless go-now | plain |

### (a) Claude-written from a fixed case grid: Exploratory: deployed v1 (vocab trim + 8-bit weights)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = deployed v1 (vocab trim + 8-bit weights) ONNX on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/12 | 13/13 | | | | |
| never go now | 12/12 | 0/13 | | | | |
| keyword list (E2) | 4/12 (9.9-65.1%) | 3/13 (5.0-53.8%) | 0/0 | 0 | 3 |  |
| deployed v1 (vocab trim + 8-bit weights) | 2/12 (2.1-48.4%) | 4/13 (9.1-61.4%) | 0/0 | 0 | 2 | 86.3 ms |

Discordant no-danger messages: b (keyword list only) = 0, c (ours only) = 1; exact McNemar p = 1.0.


### (a) Claude-written from a fixed case grid: Exploratory: v2 FP32 (second training run)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = v2 FP32 ONNX (second training run) on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/12 | 13/13 | | | | |
| never go now | 12/12 | 0/13 | | | | |
| keyword list (E2) | 4/12 (9.9-65.1%) | 3/13 (5.0-53.8%) | 0/0 | 0 | 3 |  |
| v2 FP32 (second training run) | 1/12 (0.2-38.5%) | 6/13 (19.2-74.9%) | 0/0 | 0 | 1 |  |

Discordant no-danger messages: b (keyword list only) = 0, c (ours only) = 3; exact McNemar p = 0.25.


_Exploratory, added after freeze, before tabulation: deployed board model (v2, trimmed, 8-bit weights) at the board thresholds (lo 0.068, hi 0.9). Thresholds set on Y-dev (GPT-written); the test sets are Claude-written, so the Y-dev guarantee does not formally transfer._

- (a) of the danger messages E2 misses, flagged by the board: 4/4 (39.8-100.0%)
- (b) no-danger messages flagged by the board (extra reads): 7/13 (25.1-80.8%)

### (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker (pre-registered row)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = FP32 ONNX on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/12 | 13/13 | | | | |
| never go now | 12/12 | 0/13 | | | | |
| keyword list (E2) | 2/12 (2.1-48.4%) | 3/13 (5.0-53.8%) | 0/0 | 0 | 0 |  |
| ours (registered v1 FP32) | 3/12 (5.5-57.2%) | 0/13 (0.0-24.7%) | 0/0 | 0 | 0 | 126.0 ms |

Discordant no-danger messages: b (keyword list only) = 3, c (ours only) = 0; exact McNemar p = 0.25.


Row note: The keyword list's Swahili words and every test set are Claude-written; this favours the keyword list.

Error listing:

| Arm | Message ID | Error | Class |
|---|---|---|---|
| keyword list (E2) | D02 | missed go-now | hedging, lay wording |
| keyword list (E2) | D12 | missed go-now | plain |
| keyword list (E2) | N04 | needless go-now | negation |
| keyword list (E2) | N05 | needless go-now | near-miss |
| keyword list (E2) | N10 | needless go-now | near-miss |
| ours | D01 | missed go-now | plain |
| ours | D02 | missed go-now | hedging, lay wording |
| ours | D12 | missed go-now | plain |

### (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker: Exploratory: deployed v1 (vocab trim + 8-bit weights)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = deployed v1 (vocab trim + 8-bit weights) ONNX on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/12 | 13/13 | | | | |
| never go now | 12/12 | 0/13 | | | | |
| keyword list (E2) | 2/12 (2.1-48.4%) | 3/13 (5.0-53.8%) | 0/0 | 0 | 0 |  |
| deployed v1 (vocab trim + 8-bit weights) | 3/12 (5.5-57.2%) | 0/13 (0.0-24.7%) | 0/0 | 0 | 0 | 86.3 ms |

Discordant no-danger messages: b (keyword list only) = 3, c (ours only) = 0; exact McNemar p = 0.25.


### (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker: Exploratory: v2 FP32 (second training run)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = v2 FP32 ONNX (second training run) on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/12 | 13/13 | | | | |
| never go now | 12/12 | 0/13 | | | | |
| keyword list (E2) | 2/12 (2.1-48.4%) | 3/13 (5.0-53.8%) | 0/0 | 0 | 0 |  |
| v2 FP32 (second training run) | 2/12 (2.1-48.4%) | 1/13 (0.2-36.0%) | 0/0 | 0 | 0 |  |

Discordant no-danger messages: b (keyword list only) = 3, c (ours only) = 1; exact McNemar p = 0.625.


Exploratory, per language (card language, never the text), (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker:

| Arm | Language | Danger caught | False go-now |
|---|---|---|---|
| keyword_E2 | Swahili | 10/12 (51.6-97.9%) | 3/13 (5.0-53.8%) |
| ours_registered | Swahili | 9/12 (42.8-94.5%) | 0/13 (0.0-24.7%) |
| deployed | Swahili | 9/12 (42.8-94.5%) | 0/13 (0.0-24.7%) |
| v2 | Swahili | 10/12 (51.6-97.9%) | 1/13 (0.2-36.0%) |

_Exploratory, added after freeze, before tabulation: deployed board model (v2, trimmed, 8-bit weights) at the board thresholds (lo 0.068, hi 0.9). Thresholds set on Y-dev (GPT-written); the test sets are Claude-written, so the Y-dev guarantee does not formally transfer._

- (a) of the danger messages E2 misses, flagged by the board: 2/2 (15.8-100.0%)
- (b) no-danger messages flagged by the board (extra reads): 4/13 (9.1-61.4%)

### Y-test, Claude, caregiver (pre-registered row)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = FP32 ONNX on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/80 | 55/55 | | | | |
| never go now | 80/80 | 0/55 | | | | |
| keyword list (E2) | 14/80 (9.9-27.6%) | 11/55 (10.4-33.0%) | 10/10 | 0 | 5 |  |
| ours (registered v1 FP32) | 15/80 (10.9-29.0%) | 3/55 (1.1-15.1%) | 10/10 | 0 | 5 | 126.0 ms |

Discordant no-danger messages: b (keyword list only) = 9, c (ours only) = 1; exact McNemar p = 0.0215.


Error listing:

| Arm | Message ID | Error | Class |
|---|---|---|---|
| keyword list (E2) | y_test-0001 | needless go-now | split |
| keyword list (E2) | y_test-0011 | missed go-now | lay wording, typo |
| keyword list (E2) | y_test-0015 | missed go-now | lay wording, temporal, code-mixing |
| keyword list (E2) | y_test-0019 | missed go-now | hedging |
| keyword list (E2) | y_test-0022 | needless go-now | code-mixing |
| keyword list (E2) | y_test-0031 | missed go-now | hedging, typo |
| keyword list (E2) | y_test-0032 | missed go-now | split |
| keyword list (E2) | y_test-0043 | needless go-now | negation, split |
| keyword list (E2) | y_test-0053 | missed go-now | lay wording, temporal |
| keyword list (E2) | y_test-0056 | needless go-now | near-miss, code-mixing |
| keyword list (E2) | y_test-0060 | needless go-now | plain |
| keyword list (E2) | y_test-0062 | needless go-now | near-miss |
| keyword list (E2) | y_test-0065 | missed go-now | plain |
| keyword list (E2) | y_test-0082 | needless go-now | negation, split |
| keyword list (E2) | y_test-0089 | missed go-now | plain |
| keyword list (E2) | y_test-0095 | needless go-now | negation, split |
| keyword list (E2) | y_test-0107 | missed go-now | hedging, typo |
| keyword list (E2) | y_test-0115 | missed go-now | lay wording, temporal, typo |
| keyword list (E2) | y_test-0116 | needless go-now | plain |
| keyword list (E2) | y_test-0126 | missed go-now | lay wording |
| keyword list (E2) | y_test-0130 | missed go-now | hedging, code-mixing |
| keyword list (E2) | y_test-0132 | missed go-now | plain |
| keyword list (E2) | y_test-0133 | needless go-now | near-miss |
| keyword list (E2) | y_test-0137 | missed go-now | negation, temporal, typo |
| keyword list (E2) | y_test-0145 | needless go-now | near-miss, typo |
| ours | y_test-0005 | missed go-now | plain |
| ours | y_test-0011 | missed go-now | lay wording, typo |
| ours | y_test-0012 | missed go-now | code-mixing |
| ours | y_test-0015 | missed go-now | lay wording, temporal, code-mixing |
| ours | y_test-0032 | missed go-now | split |
| ours | y_test-0038 | missed go-now | plain |
| ours | y_test-0052 | needless go-now | near-miss |
| ours | y_test-0053 | missed go-now | lay wording, temporal |
| ours | y_test-0057 | missed go-now | code-mixing, typo |
| ours | y_test-0063 | missed go-now | lay wording, code-mixing, typo |
| ours | y_test-0080 | missed go-now | hedging, code-mixing |
| ours | y_test-0089 | missed go-now | plain |
| ours | y_test-0093 | missed go-now | split |
| ours | y_test-0119 | missed go-now | hedging, lay wording, temporal |
| ours | y_test-0130 | missed go-now | hedging, code-mixing |
| ours | y_test-0132 | missed go-now | plain |
| ours | y_test-0133 | needless go-now | near-miss |
| ours | y_test-0145 | needless go-now | near-miss, typo |

### Y-test, Claude, caregiver: Exploratory: deployed v1 (vocab trim + 8-bit weights)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = deployed v1 (vocab trim + 8-bit weights) ONNX on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/80 | 55/55 | | | | |
| never go now | 80/80 | 0/55 | | | | |
| keyword list (E2) | 14/80 (9.9-27.6%) | 11/55 (10.4-33.0%) | 10/10 | 0 | 5 |  |
| deployed v1 (vocab trim + 8-bit weights) | 15/80 (10.9-29.0%) | 3/55 (1.1-15.1%) | 10/10 | 0 | 5 | 86.3 ms |

Discordant no-danger messages: b (keyword list only) = 9, c (ours only) = 1; exact McNemar p = 0.0215.


### Y-test, Claude, caregiver: Exploratory: v2 FP32 (second training run)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = v2 FP32 ONNX (second training run) on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/80 | 55/55 | | | | |
| never go now | 80/80 | 0/55 | | | | |
| keyword list (E2) | 14/80 (9.9-27.6%) | 11/55 (10.4-33.0%) | 10/10 | 0 | 5 |  |
| v2 FP32 (second training run) | 2/80 (0.3-8.7%) | 12/55 (11.8-35.0%) | 10/10 | 0 | 5 |  |

Discordant no-danger messages: b (keyword list only) = 7, c (ours only) = 8; exact McNemar p = 1.0.


Exploratory, per language (card language, never the text), Y-test, Claude, caregiver:

| Arm | Language | Danger caught | False go-now |
|---|---|---|---|
| keyword_E2 | English | 25/31 (62.5-92.5%) | 2/13 (1.9-45.4%) |
| keyword_E2 | Swahili | 21/27 (57.7-91.4%) | 7/31 (9.6-41.1%) |
| keyword_E2 | code-mixed | 20/22 (70.8-98.9%) | 2/11 (2.3-51.8%) |
| ours_registered | English | 28/31 (74.2-98.0%) | 1/13 (0.2-36.0%) |
| ours_registered | Swahili | 21/27 (57.7-91.4%) | 2/31 (0.8-21.4%) |
| ours_registered | code-mixed | 16/22 (49.8-89.3%) | 0/11 (0.0-28.5%) |
| deployed | English | 28/31 (74.2-98.0%) | 1/13 (0.2-36.0%) |
| deployed | Swahili | 21/27 (57.7-91.4%) | 2/31 (0.8-21.4%) |
| deployed | code-mixed | 16/22 (49.8-89.3%) | 0/11 (0.0-28.5%) |
| v2 | English | 30/31 (83.3-99.9%) | 2/13 (1.9-45.4%) |
| v2 | Swahili | 26/27 (81.0-99.9%) | 6/31 (7.5-37.5%) |
| v2 | code-mixed | 22/22 (84.6-100.0%) | 4/11 (10.9-69.2%) |

_Exploratory, added after freeze, before tabulation: deployed board model (v2, trimmed, 8-bit weights) at the board thresholds (lo 0.068, hi 0.9). Thresholds set on Y-dev (GPT-written); the test sets are Claude-written, so the Y-dev guarantee does not formally transfer._

- (a) of the danger messages E2 misses, flagged by the board: 14/14 (76.8-100.0%)
- (b) no-danger messages flagged by the board (extra reads): 19/55 (22.2-48.6%)

## Exploratory, not pre-registered: MASSIVE sw-KE

_Exploratory, not pre-registered: human-written Swahili (translated virtual-assistant commands, no health content); tests false alarms only, not danger detection._ Triggered go-now of 1000 (seed 20261003):

| Arm | Triggered | CP 95% |
|---|---|---|
| keyword_E2 | 43/1000 | (3.1-5.7%) |
| v1 (not shipped) fp32 | 9/1000 | (0.4-1.7%) |
| v1 (not shipped) trim10k_wq8 | 8/1000 | (0.3-1.6%) |
| v2 FP32 (not shipped) | 49/1000 | (3.6-6.4%) |
| deployed board model v2 (shipped) | 59/1000 | (4.5-7.5%) |