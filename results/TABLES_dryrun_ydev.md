# Results

Pre-registered claim (native Swahili): NOT TESTED

Tabulated once, on the sealed outputs as committed in 357f63a (freeze 28609b6). Metric code pushed before: d3dd0e9 (tables), 1d1d799 (language rows), 7b9fb58 (board rows).

### Y-dev (dry run) (pre-registered row)

_Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = FP32 ONNX on the Pi 5 (8 GB)._

| Row | Missed go-now | Needless go-now | Shared path | {c4} | "Age not received" alone | Pi p95 |
|---|---|---|---|---|---|---|
| always go now | 0/60 | 45/45 | | | | |
| never go now | 60/60 | 0/45 | | | | |
| keyword list (E2) | 10/60 (8.3-28.5%) | 2/45 (0.5-15.1%) | 10/10 | 0 | 5 |  |
| ours (registered v1 FP32) | 4/60 (1.8-16.2%) | 6/45 (5.1-26.8%) | 10/10 | 0 | 5 | 126.0 ms |

Discordant no-danger messages: b (keyword list only) = 1, c (ours only) = 5; exact McNemar p = 0.2188.


Error listing:

| Arm | Message ID | Error | Class |
|---|---|---|---|
| keyword list (E2) | y_dev-0019 | missed go-now | lay wording, temporal, typo |
| keyword list (E2) | y_dev-0025 | missed go-now | lay wording, negation, temporal, code-mixing |
| keyword list (E2) | y_dev-0028 | missed go-now | plain |
| keyword list (E2) | y_dev-0031 | missed go-now | plain |
| keyword list (E2) | y_dev-0041 | missed go-now | hedging |
| keyword list (E2) | y_dev-0046 | needless go-now | near-miss, split |
| keyword list (E2) | y_dev-0047 | missed go-now | plain |
| keyword list (E2) | y_dev-0053 | needless go-now | negation |
| keyword list (E2) | y_dev-0067 | missed go-now | lay wording, temporal, code-mixing, typo |
| keyword list (E2) | y_dev-0073 | missed go-now | lay wording, typo |
| keyword list (E2) | y_dev-0079 | missed go-now | lay wording, code-mixing |
| keyword list (E2) | y_dev-0102 | missed go-now | plain |
| ours | y_dev-0007 | missed go-now | code-mixing |
| ours | y_dev-0017 | needless go-now | near-miss |
| ours | y_dev-0046 | needless go-now | near-miss, split |
| ours | y_dev-0051 | needless go-now | near-miss |
| ours | y_dev-0073 | missed go-now | lay wording, typo |
| ours | y_dev-0076 | needless go-now | near-miss, code-mixing |
| ours | y_dev-0078 | needless go-now | near-miss, typo |
| ours | y_dev-0079 | missed go-now | lay wording, code-mixing |
| ours | y_dev-0084 | needless go-now | near-miss |
| ours | y_dev-0102 | missed go-now | plain |

Exploratory, per language (card language, never the text), Y-dev (dry run):

| Arm | Language | Danger caught | False go-now |
|---|---|---|---|
| keyword_E2 | English | 17/19 (66.9-98.7%) | 1/18 (0.1-27.3%) |
| keyword_E2 | Swahili | 18/23 (56.3-92.5%) | 1/19 (0.1-26.0%) |
| keyword_E2 | code-mixed | 15/18 (58.6-96.4%) | 0/8 (0.0-36.9%) |
| ours_fp32 | English | 19/19 (82.4-100.0%) | 4/18 (6.4-47.6%) |
| ours_fp32 | Swahili | 21/23 (72.0-98.9%) | 1/19 (0.1-26.0%) |
| ours_fp32 | code-mixed | 16/18 (65.3-98.6%) | 1/8 (0.3-52.7%) |

_Exploratory, added after freeze, before tabulation: deployed board model (v2, trimmed, 8-bit weights) at the board thresholds (lo 0.068, hi 0.9). Thresholds set on Y-dev (GPT-written); the test sets are Claude-written, so the Y-dev guarantee does not formally transfer._

- (a) of the danger messages E2 misses, flagged by the board: 10/10 (69.2-100.0%)
- (b) no-danger messages flagged by the board (extra reads): 11/45 (12.9-39.5%)
