# SafetyNet-SMS

**Pre-registered claim (native Swahili): NOT TESTED**

An assistant for Kenya's community health promoters (CHPs). The user is the health worker: she makes every clinical call. Parents in her area text a free-text SMS about a sick child (2 to 59 months) in Swahili, English or both. The assistant reads it for danger signs, tells her (with the full checklist), keeps her case board, and writes the referral and arrival record for her. When a danger sign is reported, or she is on a visit or asleep and does not reply in time, the automatic "go now" to the parent and the facility alert are a safety net, not a replacement for her. The model reads every message and puts the urgent ones in front of the health worker; it never decides what the parent is told.

Designed to sit alongside eCHIS on the health worker's government phone; integration not built this weekend. eCHIS records her visits; this assistant reads parents' SMS, flags danger signs, and writes the referral and arrival record for her instead of adding reports for her to send.

World Bank / Hack-Nation *Small AI for Development* hackathon, health track, 3 to 4 October 2026.

> SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway. Everything behind the gateway runs as shown, on this Pi. Synthetic cases; not clinically validated.

## How it works

The model runs on her phone. Where phones fail, the same model runs on a county box behind the SMS number. That box is what we demoed. The parent still gets "go now" and the facility is still alerted when her phone is off or broken.

- **One endpoint.** `POST /sms {from, to, body}`; the role (parent, health worker, facility) comes from the number texted. A 3-pane web simulator (Parent / Health worker / Facility + CHA) is the demo client. A gateway adapter (Africa's Talking or a county shortcode in Kenya; Twilio elsewhere) is a thin mapping onto this endpoint and is not built.
- **Parent line.** The parent only ever gets one of five fixed messages: go now, go now (unregistered number), your health worker has been told (with a waiting time and the danger-sign list), the health worker did not reply (go now), or not for this number. The parent is never asked a question and never gets advice, reassurance, a diagnosis, a medicine or a dose. A send-time check refuses any other text to a parent.
- **Health-worker line.** Deterministic: a regex and a fixed keyword list read the text for signs that are present; nothing is ever read as absent. The health worker gets the full 8-option checklist and only a numbered reply ("0") clears a sign. Any sign, "9", silence or two unreadable replies refer.
- **Case board.** In the health-worker pane: her cases with code, age, a danger flag, the signs recorded, status (to check / referred / no reply / arrived / closed) and time, danger first, then oldest. Built only from stored case records; nothing generated. After an arrival it shows "follow-up visit due {date}", after she closes a case with "0" "check on child due {date}" (3 days, WHO/UNICEF CHW manual pp.98 and 116); these say only when to go back and are never sent as SMS.
- **Referral loop.** Every referral sends an alert with a 4-digit code to the facility and the community health assistant (CHA). The facility texts the code on arrival; the health worker and CHA are told the child arrived. The facility owns the arrival code. No reply to a code means it was not recorded: resend.
- **Rules.** `config/protocol.yaml` holds the RED (refer) rules from the WHO/UNICEF community case management materials, editable by the ministry. Must-stay-RED tests (T1 to T35, T34 retired) and caregiver tests (CG1 to CG18, CG16 retired) run on every load: a protocol edit that drops a RED rule is refused, and any red caregiver test switches the parent door off.

## Runs on a phone-class device

The model runs on the health worker's own phone, with no internet or data bundle; SMS is the only channel. Where her phone fails, the same model runs on a county box behind the SMS number: still no internet, but a shared local server rather than her device. In this demo a Raspberry Pi plays both roles.

> The same 90 MB model runs offline in a phone browser (iPhone, Safari: p95 170 ms; a best case, since entry-level Android phones are slower). On a Raspberry Pi 5 limited to 1 core, the whole service peaked at 549 MB of RAM, about a quarter of a 2 GB phone's memory (Android itself uses part of it): p95 516 ms per parent message, end to end. Not yet measured on an entry-level Android; no phone app was built this weekend.

**In a phone browser (P4).** The shipped board model (v2, trimmed, 8-bit weights, 89.7 MB) runs in Safari on an iPhone, single-threaded WebAssembly (onnxruntime-web 1.30), served once from the Pi over the local network with no CDN: 50 Y-dev messages p50 109 ms, p95 170 ms; model load 1.3 s (user agent `Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.7.5 Mobile/15E148 Safari/604.1`). Parity with the Pi on 20 Y-dev messages: tokens 20/20, head flags 20/20, board bands 20/20, largest probability difference 0.021. With airplane mode on and Wi-Fi off the status line read "Offline" and typed messages were still read. Works offline once loaded; a reload needs the network (no HTTPS service worker in this build). The tokenizer is a small JavaScript Unigram implementation of the same `tokenizer.json`.

**Pi limited to 1 core (headroom).** The full service (rules, keyword list, board model) pinned to one core with `taskset -c 0`: 50 Y-dev parent messages end to end p50 397 ms, p95 516 ms, max 718 ms; peak RSS 549 MB. The 2 GB memory cap (`systemd-run --user -p MemoryMax=2G`) was not enforced: this Pi's user session delegates only the cpu and pids cgroup controllers, and a system scope needs root. Note: the 2 GB cap could not be enforced without root (the cgroup memory controller is not delegated to the user session); peak RSS was measured instead.

The parent line runs the keyword list live; the model was scored on the Pi (single pass, frozen), not used live, because it failed the caregiver safety tests. The tables below show the model the tool would ship once it passes the caregiver tests.

### What fits on which phone, and what it costs

All variants come from the same fine-tuned v1 model. Size = model + tokenizer on disk. Peak RAM, cold load and p95 per message (64 tokens) measured on the Pi 5 with ONNX Runtime (4 cores, and pinned to 1 core with `taskset`). Accuracy on Y-dev (GPT-written development set, 120 messages: 60 danger, 45 no-danger), never on a test set. Rule: deploy the smallest variant with >= 99% go-now agreement with FP32 on Y-dev and no danger message missed that FP32 catches.

| Variant | Size MB | Peak RAM MB | Load s | p95 ms, 4 cores | p95 ms, 1 core | Danger caught | False go-now | Agrees with FP32 | Danger missed vs FP32 | Passes |
|---|---|---|---|---|---|---|---|---|---|---|
| FP32 (registered default) | 1074.9 | 1851 | 2.2 | 126.0 | 373.2 | 56/60 | 6/45 | 120/120 | 0 | yes |
| INT8 dynamic, MatMul only (registered INT8) | 832.1 | 1610 | 1.75 | 44.4 | 116.8 | 26/60 | 3/45 | 87/120 | 30 | no |
| INT8 dynamic, MatMul only, per-channel | 832.5 | 1611 | 1.78 | 46.0 | 119.8 | 49/60 | 6/45 | 113/120 | 7 | no |
| INT8 dynamic incl. embeddings (Gather) | 281.6 | 625 | 1.21 | 45.7 | 117.2 | 27/60 | 4/45 | 89/120 | 29 | no |
| INT8 weight-only (per-channel), FP32 compute | 283.1 | 1432 | 1.47 | 182.1 | 317.3 | 56/60 | 6/45 | 120/120 | 0 | yes |
| Vocab trim (9,759 tokens), FP32 | 355.4 | 490 | 0.82 | 158.4 | 364.6 | 56/60 | 6/45 | 120/120 | 0 | yes |
| Vocab trim + INT8 dynamic, MatMul only | 112.6 | 252 | 0.4 | 46.0 | 116.9 | 26/60 | 3/45 | 87/120 | 30 | no |
| Vocab trim + INT8 dynamic incl. embeddings | 90.0 | 228 | 0.39 | 45.6 | 117.7 | 28/60 | 4/45 | 90/120 | 28 | no |
| Vocab trim + INT8 weight-only (per-channel) | 90.3 | 322 | 0.63 | 86.3 | 215.9 | 56/60 | 6/45 | 120/120 | 0 | yes |
| Keyword list E2 (no model; runs the parent line live), for reference | | | | | | 50/60 | 2/45 | | | |
| Keyword list v0 (no model), for reference | | | | | | 30/60 | 3/45 | | | |

INT4 (MatMulNBits) was not built: its export failed on the first try. Activation-quantized INT8 (the registered INT8 and its variants) fails the rule badly: it pushes many danger probabilities below 0.5. Weight-only INT8 stores the weights as 8-bit and computes in FP32.

### On-device card (deployed variant)

| | Deployed: vocab trim + weight-only INT8 | Registered: FP32 (reference) |
|---|---|---|
| File size | 90.3 MB | 1074.9 MB |
| Peak RAM | 322 MB (2 GB phone: Android itself uses part of this RAM) | 1851 MB |
| Cold load | 0.63 s | 2.2 s |
| p50 / p95 at 64 tokens, 4 cores | 82.7 / 86.3 ms | 125.6 / 126.0 ms |
| p95 at 64 tokens, 2 cores | 118.2 ms | 192.1 ms |
| p95 at 64 tokens, 1 core | 215.9 ms | 373.2 ms |

Entry-level Android phone in Kenya: {spec line, cited in DATA.md}

CPU clock was not reduced for the headroom test: changing the Pi's cpufreq limit needs root, so only core pinning was used.

### The model on the health worker's board

The model reads every message and puts the urgent ones in front of the health worker; it never decides what the parent is told. It sorts the health worker's cases and marks the ones it is unsure about for her to read first.

It reads parent text only and adds one of three board lines, from its calibrated top danger probability: "model: possible {sign}, check" (at or above hi), "model unsure: please read" (between lo and hi), or nothing (below lo). The board sorts rule-flagged danger first, then "possible", then "unsure", then the rest, oldest first within each group. It sends no SMS and changes no case status; a model failure just leaves no model line. Tested: the parent reply is identical with the model on and off (CG1 to CG18 both ways).

Model: v2, vocabulary-trimmed with 8-bit weights (89.7 MB). Calibration: one temperature per head, fit on X-val (held out from the GPT-written training data; never Y-dev or a test set):

| Head | Temperature | ECE before | ECE after |
|---|---|---|---|
| convulsions | 0.6 | 0.0477 | 0.012 |
| not_drink_feed | 0.25 | 0.0319 | 0.0 |
| vomits_everything | 0.35 | 0.041 | 0.0039 |
| sleepy_unconscious | 0.6 | 0.0382 | 0.0103 |
| blood_stool | 0.65 | 0.043 | 0.0127 |
| cough_long | 0.4 | 0.0585 | 0.0105 |
| diarrhoea_long | 0.5 | 0.0593 | 0.0243 |
| fever_long | 0.6 | 0.0502 | 0.0127 |

Thresholds, set on Y-dev (GPT-written): lo = 0.068 (the lowest Y-dev danger score: no Y-dev danger message falls below it; with 60 danger messages this bounds the miss rate at roughly 1/61 on data like Y-dev), hi = 0.9 (see the decision below the table). Sweep on Y-dev:

| lo | hi | Y-dev messages sent to "please read" | Y-dev danger messages below lo (of 60) | Y-dev no-danger marked "possible" (of 45) |
|---|---|---|---|---|
| 0.068 | 0.9904 (data-driven) | 30.8% | 0 | 0 |
| **0.068 (chosen)** | **0.9 (chosen)** | **12.5%** | **0** | **2** |
| 0.01 | 0.9 | 13.3% | 0 | 2 |
| 0.01 | 0.95 | 16.7% | 0 | 2 |
| 0.1 | 0.9 | 10.0% | 1 | 2 |
| 0.1 | 0.95 | 13.3% | 1 | 2 |
| 0.2 | 0.9 | 9.2% | 1 | 2 |
| 0.2 | 0.95 | 12.5% | 1 | 2 |
| 0.5 | 0.9 | 5.8% | 2 | 2 |
| 0.5 | 0.95 | 9.2% | 2 | 2 |

Board threshold hi = 0.9 (chosen on Y-dev before the freeze, Sat 3 Oct). At hi = 0.9904, no Y-dev no-danger message was marked 'possible', but 30.8% of messages went to 'please read' and 'possible' almost never fired. At hi = 0.9, review load falls to 12.5%, at the cost of 2 of 45 Y-dev no-danger messages marked 'possible'. On the board a false 'possible' only moves a case up the health worker's list: no SMS is sent and no case status changes. A review load of about a third of all messages risks the health worker ignoring the flags (mTrac's on-time volunteer reporting fell from 60% to 9%; DFID 2014 via SDSN TReNDS 2018). lo = 0.068 is unchanged, so no Y-dev danger message falls below it. The full sweep is in the table above.

## Safety contract and preconditions

- Messages to health workers, facilities and the CHA are English only. Parent messages: the four go-now and not-for-this-number messages are bilingual, Swahili first and English below as the authoritative line; "your health worker has been told" is sent in the parent's registered language (Swahili by default, or English). Swahili messages machine-translated (gpt-5.5) and back-translation-checked (claude-opus-5-5); native-speaker and clinician review required before any deployment.
- A parent message without the child's age is sent to the facility at once; this over-refers on purpose.
- Caregiver path not clinically validated.
- If any caregiver safety test fails at start-up, the parent door switches off; a parent text then gets the fixed "take the child to the nearest health facility NOW" reply without being read, and the CHA gets a copy. The parent line is never silent.
- No text is ever read as absent; only a numbered reply clears a sign. Enforced by T1 to T35 and CG1 to CG18 on every load; not counted on the eval sets.
- Numbers not in the registry are always sent to the facility; in production the CHP would add the number at household registration.
- A Swahili report that the child is worse is not read as go-now; the parent still gets the deadline and the health worker is called.
- A negation before another word can hide a sign; the parent still gets the danger-sign list and the deadline.
- Swollen feet in other words do not send the parent at once; the health worker is called and answers the full checklist, which asks about both feet (option 8).
- MUAC and feet rest on the health worker's 0; there is no separate measuring step.
- On the health-worker line, a sign typed in words the keyword list misses is asked in the full checklist, not referred at once.
- Demo timeouts are 60 seconds. In production the reply window (60 minutes, at most 120) is agreed with the county.
- Retention: in production, message text is deleted 7 days after a case closes (the county sets the period). Not implemented in this build: the demo database keeps message text and the synthetic demo numbers.
- Precondition for deployment: a county shortcode on a Kenyan SMS gateway, so parents pay nothing. Texts sent while the box is down are lost.
- Not clinically validated.

## Responsible AI

### Where the data sits, who reads it, lost or shared phone

- **Where.** Cases live on the health worker's phone (DESIGN); in this demo, a SQLite file on the Raspberry Pi (BUILT). No cloud (BUILT). The model has no network access (BUILT).
- **What leaves the device.** Only fixed SMS to the parent; the facility alert (case code, age, signs; no name, no sex); escalations to the CHA (BUILT).
- **Who reads it.** The health worker; the facility, alerts only; the CHA, escalations only (BUILT). SMS is plain text, so the mobile carrier can read it.
- **No names.** The tool asks for no name and has no name field (BUILT; tested: no name column, no name slot in any message, no parent words in any outgoing SMS or case record). A parent may still type one, and that text stays in the case log. Names stay in the health worker's existing household register.
- **Retention.** Case content is deleted 30 days after closure; that's our default and the ministry sets it (`retention_days` in `config/protocol.yaml`) (BUILT; tested).
- **Lost or shared phone.** An app PIN separate from the phone unlock (DESIGN); notifications show no content (DESIGN); the CHA deletes the phone's line in the number-to-role registry, after which that number gets no case data (BUILT); Android Find My Device to wipe (DESIGN).
- **Gap.** Parent texts also sit in the phone's SMS inbox, as they do today when parents text a health worker.

Under Kenya's Data Protection Act 2019 (No. 24 of 2019), "health status" is sensitive personal data (s.2), and health data "may only be processed (a) by or under the responsibility of a health care provider; or (b) by a person subject to the obligation of professional secrecy under any law" (s.46(1)), so a deployment would run under a health care provider, not the hackathon team. Source: Kenya Law, https://new.kenyalaw.org/akn/ke/act/2019/24/eng@2022-12-31

### Consent

**Consent.** The health worker registers a parent's number at a household visit, after explaining in Swahili or English what the number does and what the facility will see, and that a program on her phone reads each message first to sort her cases, and notes verbal consent in her existing household register (DESIGN). Only registered numbers open a full case; an unregistered number gets only the fixed "go to the nearest facility now" reply and a CHA copy, and nothing else is stored about it beyond the case log (BUILT). A parent can opt out at any time by telling the health worker, who removes the number from the registry (DESIGN; removal itself is BUILT). An SMS "STOP" keyword is not built (DESIGN).

### Bias and who it may fail

**Bias and who it may fail.** The model was trained on GPT-written messages and tested on Claude-written messages, in Swahili, English and code-mixed text; no message written by a real parent or health worker was used, and no native speaker checked them (see DATA.md). It is untested on Kikuyu, Luo and Sheng; AfroXLMR was not trained on Kikuyu, and Luo was not in its training (DATA.md, M1), so we expect it to do worse there. The keyword list is also Swahili and English only, so in Kikuyu, Luo or Sheng both can miss. The backstop is the danger list in every reply and the health worker reading every message. Because the model never decides what the parent is told, a miss in an untested language leaves the case where the keyword list put it, and the health worker still reads every message. The drift monitor counts model-vs-health-worker disagreements by language each week, so a group of parents the model fails shows up as a rising count (DESIGN). Results by language are reported as an exploratory row, using each test message's language as fixed when the data was generated.

### Human in the loop

The tool never decides against care. Only a health worker can close a case, and only by replying "0" (none of the danger signs, all checked) after seeing the child. Every other path ends with a person: the health worker is called, the facility and CHA are alerted, and the facility confirms arrival. The model can only add a reason to send a child now; it can never remove one.

### The fail-safe

When the tool is not sure, it sends the child or calls a person; it never guesses "fine". A message it cannot read, a missing age, a silent health worker, a health worker who replies "9" (not sure), a model that fails to load: each one ends in "go now" for the parent or in the health worker being told, with a deadline. If a caregiver safety test fails at start-up, the parent line falls back to a fixed "go to the nearest health facility NOW" reply and the CHA is told; it is never silent.

### Drift and bias monitor

**Drift and bias monitor (DESIGN).** Each case logs the model's flags next to the health worker's checklist answers. A weekly count of disagreements, by sign and by language, goes to the CHA. A rising count means the model is drifting or failing a group of parents, and is the trigger to review it.

## Where the record lands

**The data gap this fills.** Nobody routinely knows whether a referred child reaches the facility. In one Kenyan sub-county, of 112 children referred for pneumonia by community volunteers, referral forms were on file at the hospital for 19 (DATA.md, P8). This tool writes the missing record as a side effect of care: a referral when the case opens and an arrival when the facility texts the code back (BUILT). Those two records are what a referral-completion rate needs, and they are designed to flow into eCHIS and, as eCHIS data is reported to sync to KHIS, into Kenya's national DHIS2 instance (DESIGN).

**Where the record lands (DESIGN, not built).** Each case produces two records: a referral (case code, child's age, CHP, danger signs flagged, time sent) and an arrival (facility, time seen). In a real deployment these would be sent to eCHIS, the Ministry of Health's community health app built on Medic's Community Health Toolkit, which already includes client referral. eCHIS data is reported to sync to KHIS, Kenya's national DHIS2 instance, so counts would roll up there. No public inbound API is confirmed. The demo writes the same fields to a local database.

Sources: Medic, 2023 (https://medic.org/stories/accompanying-kenyas-ministry-of-health/ ; https://medic.org/stories/cht-interoperability-reference-application-adoption-by-ministry-of-health-kenya-to-facilitate-data-exchange/); Living Goods, 16 Oct 2023, sync (secondary) (https://livinggoods.org/media/kenya-takes-bold-step-towards-universal-health-coverage-with-the-launch-of-a-digital-health-tool/); DHIS2.org, 10 Aug 2026 (https://dhis2.org/kenya-launches-dhis2-for-case-based-eye-care-program/).

## Production gaps

- A keyed hash of phone numbers.
- 3-segment delivery on Kenyan basic phones untested.
- Gateway request validation.
- The reply window agreed with the county.
- A health worker may answer the checklist after a phone call only.
- Same age = same child, so twins are a residual.
- An unknown number gets Swahili + English in one SMS (built Sat 3 Oct); the Swahili still needs native-speaker and clinician review.
- **Known over-referral bugs in the shared age regex (safe direction, both eval arms, not fixed).** (1) A number of days with no symptom word before it is read as the child's age, so the message goes to "under 2 months": "wide awake 2day", "homa since jana, 2 days", "It has been 5 days now with the cough", "ameharisha siku 5" ("ameharisha" is not in the symptom-word list). (2) "1yr 1 month" is read as two ages and the youngest (1 month) decides. Not fixed during the event because a fix could stop real newborn ages ("mtoto wa siku 5") from reaching "under 2 months", which would be a safety regression.

## Built during the event

All project code was written after 12:00 ET on Sat 3 Oct 2026. Made before the event and disclosed: planning documents, the pre-registration (`PREREGISTRATION.md`, tag `prereg`) and test set (a) (`tests/caregiver_set_a.csv`, Claude-written test data, commit b492142). `docs/privacy.html` and `docs/terms.html` (SMS privacy policy and terms) were added on 1 Oct for SMS carrier registration and are not project code.

## Changes after pre-registration

- Before sealing, rows D10 and N03 of set (a) were corrected for format (age present; duration clearly over 14 days; no breathing/chest/"worse" words), and Florian saw those two rows' text; the other 23 rows were not read.
- "miaka" added as a year unit on Sat 3 Oct, before any test set was opened; source: the system's pre-event Swahili onboarding text.
- "umri N" without a unit is treated as no age (an age needs a unit).
- **Deployment rule and deployed model.** Extends prereg section 7: deploy the smallest variant with at least 99% go-now agreement with FP32 on Y-dev and no danger message missed that FP32 catches, chosen on Y-dev before `freeze`. Deployed: the v1 model with its vocabulary trimmed after fine-tuning to 9,759 tokens (keep-list: single Latin characters, X train, the keyword lists, the fixed strings, MASSIVE train) and weights stored as 8-bit (weight-only, per channel), 90.3 MB with tokenizer (FP32: 1,074.9 MB). Reason: the brief's rule that model files must be small enough to side-load or send over a weak connection. The registered row stays FP32 as pre-registered (the registered INT8 failed the section 7 rule); the deployed variant is reported as its own labelled row.
- **Rung 3.** The parent line runs the keyword list live; the model was scored on the Pi (single pass, frozen), not used live, because it failed the caregiver safety tests (CG1 and CG5 with the encoder on) and the Y-dev go-live gate (more needless go-nows than the keyword list).
- **v2.** A second training run (v2) added terse and negated messages after the v1 encoder failed the caregiver safety tests CG1/CG5; training on short danger-term messages makes CG1 easier to pass, which we consider legitimate because recognising bare danger terms is what CG1 requires. v2 still failed (CG5, CG5b, CG10, CG12 and the Y-dev gate) and is reported as its own labelled row.
- **Board use of the v2 model.** The v2 model runs on the health worker's case board only, with calibrated probabilities and a "please read" band (thresholds set on Y-dev); the parent line is unchanged and stays rule-based. Its test-set numbers are an exploratory row: thresholds set on Y-dev (GPT-written); the test sets are Claude-written, so the Y-dev guarantee does not formally transfer.
- **Board threshold.** Board threshold hi = 0.9 (chosen on Y-dev before the freeze, Sat 3 Oct). At hi = 0.9904, no Y-dev no-danger message was marked 'possible', but 30.8% of messages went to 'please read' and 'possible' almost never fired. At hi = 0.9, review load falls to 12.5%, at the cost of 2 of 45 Y-dev no-danger messages marked 'possible'. On the board a false 'possible' only moves a case up the health worker's list: no SMS is sent and no case status changes. A review load of about a third of all messages risks the health worker ignoring the flags (mTrac's on-time volunteer reporting fell from 60% to 9%; DFID 2014 via SDSN TReNDS 2018). lo = 0.068 is unchanged, so no Y-dev danger message falls below it. The full sweep is in the table above.
- **P2.** P2 (decided Sat 3 Oct after the freeze, on Y-dev only, before any test tabulation): letting the model add a 'go now' to the parent line was not adopted. Every variant failed CG5/CG5b (the models misread Swahili denials) and raised false 'go now' by more than 2 points on Y-dev. The model stays on the health worker's board only.
- **Parent languages.** Parent messages became bilingual / in the parent's registered language (Florian, Sat 3 Oct, after the freeze; the pre-registered evaluation scores the go-now decision, not the wording). Swahili messages machine-translated (gpt-5.5) and back-translation-checked (claude-opus-5-5); native-speaker and clinician review required before any deployment.
- **Waiting time.** CG_TOLD now states a waiting time in minutes instead of a clock time, because Swahili clock time runs 6 hours off standard time. The English version grows from 2 to 3 SMS segments at the longest window (120 minutes).
- **Exploratory row (not pre-registered).** MASSIVE sw-KE: human-written Swahili (translated virtual-assistant commands, no health content); tests false alarms only, not danger detection.

## Word lists added on Saturday (from the protocol sources only)

- Under 2 months: "newborn" (S10). Pregnancy and adult words: "pregnant", "pregnancy", "adult".
- Swahili newborn and pregnancy terms: none in the protocol sources; such messages without an age fall to "go now, age not received".
- Duration symptom words: cough, kikohozi; diarrhoea, diarrhea, kuhara; fever, homa. The Swahili words come from the pre-event ASK_SIGNS option 7 ("Siku: kikohozi 14+, kuhara 14+, homa 7+").
- Hedges: "labda", "?". "about a week" and "a week" count as 7 days. Numbers written as words are not read.
- Swahili keyword and test words come from AI-drafted planning text that no native speaker checked.

## Does it fit the sector's challenges, and what constraints does it add?

| Challenge in the health annex / persona | How SafetyNet-SMS fits |
|---|---|
| Parents on basic phones, no data bundles (only 27.5% of rural women own a smartphone, DATA.md F1) | Parent side is plain SMS on any phone; no app, no data (BUILT) |
| 2G/3G networks | SMS only; the model needs no internet (BUILT) |
| Low digital literacy | Parent is never asked a question; fixed short messages (BUILT). Voice not built |
| Clinician time and heavy load | Danger cases sorted first; checklist with numbered replies; facility gets one short alert (BUILT) |
| Burdensome record-keeping | Referral and arrival records written automatically (BUILT) |
| No new hardware for the user | Runs on the health worker's existing phone (DESIGN); the demo box is a stand-in and a county backup |
| Local language | Parents write in Swahili, English or both; the four urgent replies are bilingual, the longer one is in the parent's language (BUILT as a mechanism; the Swahili strings are machine-translated, not native-reviewed, and go live only after Florian approves them) |
| Privacy (where data sits, lost phone) | See "Where the data sits" (BUILT/DESIGN marked) |

**Constraints we add.**
- The health worker needs an Android phone with about 322 MB free memory (peak RAM of the deployed model on the Pi) and 90.3 MB storage; reported CHP phones have 2 GB RAM (DATA.md, C5), and Android uses part of that.
- Someone pays for the SMS: average KES 1.18 per message (DATA.md, F3); a case uses 4 to 10 outgoing messages (7 to 13 SMS segments), counted from scripted runs of the demo flows: told then no danger sign 4 (8 segments), parent go-now then arrival 7 (7), told then referred then arrival 10 (13).
- The parent needs access to any phone, often shared; women are less likely than men to own one (DATA.md, F2).
- The parent must read Swahili or English (replies: see the Swahili note).
- Facilities must text the arrival code back; a facility that doesn't leaves the case open and escalates to the CHA (BUILT).

## Reuse in another setting

- **What changes:** the protocol file (`config/protocol.yaml`, edited by the ministry, checked by the must-stay-RED tests on every load); the facility and health worker registry; the fixed messages (reviewed once by a native speaker and a clinician); the model, retrained on local messages.
- **What stays:** the workflow, the safety tests, the fail-safe, the case board.
- **Cost to add a language (measured this weekend):** 1,794 generated training and development messages (gpt-5.5: 1,200 X train, 474 v2 additions, 120 Y-dev) plus 175 generated test messages (claude-opus-5-5); API cost not logged this weekend; fine-tuning 0.4 GPU-minutes per run on one desktop GPU (RTX 4070 Ti SUPER; v1 measured); deployed model 89.7 MB (90.3 MB with tokenizer); the whole build, from the first generation commit to the frozen results, took about 2 hours 10 minutes of wall-clock (git log: 12:21 to 14:31 ET, Sat 3 Oct). Real deployment would replace generated messages with messages written by local parents and health workers.
- **Running cost:** SMS at about KES 1.18 each (DATA.md, F3); no cloud.
- **Pilot plan:** one CHU, the CHA reviews every model flag for the first weeks before anyone relies on it.

## Results

**Pre-registered claim (native Swahili): NOT TESTED**

Tabulated once, at tag `results`, on the outputs sealed at `freeze` (28609b6, pushed 14:06 ET Sat 3 Oct). Full tables, error listings by message ID and class, and errata: `results/TABLES.md`, `results/ERRATA.md`.

Outcome (checked in the pre-registered order: safety switch, then Win, then Tie-or-loss). The safety switch fired on (b) and Y-test.

> No native speaker's texts were sealed in time, so my registered claim is not tested. On three stand-in sets, the model sent 10 of 12 children with a danger sign to the clinic in 25 test messages an AI model wrote from a fixed case grid, 9 of 12 in 25 AI-written Swahili texts no native speaker checked, and 65 of 80 in 150 AI-written test texts; the keyword list 8, 10, 66. Needless trips: model 4 of 13, 0 of 13, 3 of 55; keyword list 3, 3, 11. None are real parents' texts, so the model is not shown to beat a keyword list.

On screen with it: "Test messages written by an AI model from a fixed case grid; no native or human-written test set."

> Before testing I set a rule that the model may not miss more children with a danger sign than a keyword list; on (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker it missed 3 of 12, the keyword list 2, so the keyword list now runs the parent line.

> Before testing I set a rule that the model may not miss more children with a danger sign than a keyword list; on Y-test, Claude, caregiver it missed 15 of 80, the keyword list 14, so the keyword list now runs the parent line.

Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = FP32 ONNX on the Pi 5 (8 GB).

| Set | Row | Missed go-now (CP 95%) | Needless go-now (CP 95%) | Shared path | "Age not received" alone |
|---|---|---|---|---|---|
| (a) Claude-written from a fixed case grid | keyword list (E2) | 4/12 (9.9-65.1%) | 3/13 (5.0-53.8%) | 0/0 | 3 |
| (a) Claude-written from a fixed case grid | ours (registered v1 FP32) | 2/12 (2.1-48.4%) | 4/13 (9.1-61.4%) | 0/0 | 2 |
| (a) Claude-written from a fixed case grid | McNemar (no-danger discordant) | b = 0, c = 1 | p = 1.0 | | |
| (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker | keyword list (E2) | 2/12 (2.1-48.4%) | 3/13 (5.0-53.8%) | 0/0 | 0 |
| (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker | ours (registered v1 FP32) | 3/12 (5.5-57.2%) | 0/13 (0.0-24.7%) | 0/0 | 0 |
| (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker | McNemar (no-danger discordant) | b = 3, c = 0 | p = 0.25 | | |
| Y-test, Claude, caregiver | keyword list (E2) | 14/80 (9.9-27.6%) | 11/55 (10.4-33.0%) | 10/10 | 5 |
| Y-test, Claude, caregiver | ours (registered v1 FP32) | 15/80 (10.9-29.0%) | 3/55 (1.1-15.1%) | 10/10 | 5 |
| Y-test, Claude, caregiver | McNemar (no-danger discordant) | b = 9, c = 1 | p = 0.0215 | | |

Baselines: always go now misses 0 and sends every no-danger child; never go now misses every danger child. Only a native set could produce a Win, so the Y-test McNemar p is not a win.

### Summary for the video (`results/video_table.png`)

| | Keywords | Pre-registered model (v1) | Retrained model, board (v2) |
|---|---|---|---|
| Danger missed: (a) grid | 4 / 12 | 2 / 12 | 1 / 12 |
| Danger missed: (b) Swahili | 2 / 12 | 3 / 12 | 2 / 12 |
| Danger missed: Y-test | 14 / 80 | 15 / 80 | 2 / 80 |
| **Danger missed: total** | **20 / 104** | **20 / 104** | **5 / 104** |
| **Needless trips: total** | **17 / 81** | **7 / 81** | **19 / 81** |
| **False alarms, 1,000 everyday Swahili sentences written by people (MASSIVE, not about health)** | **43** | **9** | **59** |

The board runs the 90 MB version of the retrained model (agreed with the full-size one on 119 of 120 dev messages); its MASSIVE count is the 90 MB version (full-size: 49). Test sets are AI-written. The v2 column is exploratory (a second training run after the freeze); the pre-registered comparison is keywords vs v1.

### Exploratory rows (not pre-registered)

| Set | Row | Missed go-now | Needless go-now |
|---|---|---|---|
| (a) Claude-written from a fixed case grid | v1 deployed (trim + 8-bit weights) | 2/12 (2.1-48.4%) | 4/13 (9.1-61.4%) |
| (a) Claude-written from a fixed case grid | v2 FP32 (second training run) | 1/12 (0.2-38.5%) | 6/13 (19.2-74.9%) |
| (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker | v1 deployed (trim + 8-bit weights) | 3/12 (5.5-57.2%) | 0/13 (0.0-24.7%) |
| (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker | v2 FP32 (second training run) | 2/12 (2.1-48.4%) | 1/13 (0.2-36.0%) |
| Y-test, Claude, caregiver | v1 deployed (trim + 8-bit weights) | 15/80 (10.9-29.0%) | 3/55 (1.1-15.1%) |
| Y-test, Claude, caregiver | v2 FP32 (second training run) | 2/80 (0.3-8.7%) | 12/55 (11.8-35.0%) |

**By language (exploratory; each message's language as fixed when it was generated, never read from the text; set (a) has no language split).**

| Set | Language | Keyword list E2 | v1 FP32 (registered) | v2 FP32 |
|---|---|---|---|---|
| (b) | Swahili | 2/12 missed, 3/13 needless | 3/12 missed, 0/13 needless | 2/12 missed, 1/13 needless |
| Y-test | Swahili | 6/27 missed, 7/31 needless | 6/27 missed, 2/31 needless | 1/27 missed, 6/31 needless |
| Y-test | English | 6/31 missed, 2/13 needless | 3/31 missed, 1/13 needless | 1/31 missed, 2/13 needless |
| Y-test | code-mixed | 2/22 missed, 2/11 needless | 6/22 missed, 0/11 needless | 0/22 missed, 4/11 needless |

**The board model (exploratory).** Deployed board model v2 (trimmed, 8-bit weights) at the board thresholds lo 0.068 / hi 0.9. On Y-dev, where the thresholds were set (thresholds set on this data), it flagged 10 of the 10 danger messages the keyword list E2 missed, and flagged 11 of 45 no-danger messages. On the sealed sets (thresholds set on Y-dev; the test sets are Claude-written, so the Y-dev guarantee does not formally transfer):

| Set | Danger messages E2 missed that the board flagged | No-danger messages flagged |
|---|---|---|
| (a) Claude-written from a fixed case grid | 4/4 (39.8-100.0%) | 7/13 (25.1-80.8%) |
| (b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker | 2/2 (15.8-100.0%) | 4/13 (9.1-61.4%) |
| Y-test, Claude, caregiver | 14/14 (76.8-100.0%) | 19/55 (22.2-48.6%) |

**Human-written Swahili with no health content: MASSIVE sw-KE (exploratory).** On 1,000 translated virtual-assistant commands (sampled with a fixed seed), counted as "go now" triggered by a sign, a C4 word or under 2 months, the keyword list triggered on 43, the first model (v1 FP32) on 9, and the shipped board model (v2, trimmed, 8-bit weights) on 59. All model counts use the parent-line rule (raw p >= 0.5 on any head), not the board's calibrated bands. v2 differs from v1 by 462 extra training messages, terse danger terms and negated lists, added after v1 failed the caregiver tests CG1 and CG5; v2 ships on the board because on Y-dev it passed more caregiver tests and caught more danger messages, and it was chosen there before the freeze. When each number was seen: the v1 FP32, v2 FP32 (49) and keyword list counts printed when the runs finished, after the freeze and after v2 had already been chosen for the board; the shipped v2 count was run after the freeze, before the tabulation. So on the AI-written test sets v1 (the registered model) had fewer needless trips than the keyword list, but on human-written Swahili the shipped v2 raised more "go now" triggers than the keyword list did.

### Evaluation notes

- Training and development data were written by GPT; every test set was written by Claude.
- Test messages written by an AI model from a fixed case grid; no native or human-written test set.
- Y labels not hand-checked.
- Scored single-pass: each message read once, first reply scored; the dialogue was not replayed. Dialogue behaviour is checked only by must-stay-RED tests T1 to T35 and CG1 to CG18.

## Run it

```
python -m app.check                     # load the protocol, run T1-T35, CG1-CG18 and the lints
python -m pytest checks                 # unit and flow tests
python -m uvicorn app.server:app --host 0.0.0.0 --port 8000   # endpoint + simulator at /
```
On the Pi: `sh scripts/pi_run.sh`.
