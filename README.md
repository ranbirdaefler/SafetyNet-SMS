# SafetyNet-SMS

**Pre-registered claim (native Swahili): NOT TESTED**

An assistant for Kenya's community health promoters (CHPs). The user is the health worker: she makes every clinical call. Parents in her area text a free-text SMS about a sick child (2 to 59 months) in Swahili, English or both. The assistant reads it for danger signs, tells her (with the full checklist), keeps her case board, and writes the referral and arrival record for her. When a danger sign is reported, or she is on a visit or asleep and does not reply in time, the automatic "go now" to the parent and the facility alert are a safety net, not a replacement for her.

Designed to sit alongside eCHIS on the health worker's government phone; integration not built this weekend. eCHIS records her visits; this assistant reads parents' SMS, flags danger signs, and writes the referral and arrival record for her instead of adding reports for her to send.

World Bank / Hack-Nation *Small AI for Development* hackathon, health track, 3 to 4 October 2026.

> SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway. Everything behind the gateway runs as shown, on this Pi. Synthetic cases; not clinically validated.

## How it works

The model runs on her phone. Where phones fail, the same model runs on a county box behind the SMS number. That box is what we demoed. The parent still gets "go now" and the facility is still alerted when her phone is off or broken.

- **One endpoint.** `POST /sms {from, to, body}`; the role (parent, health worker, facility) comes from the number texted. A 3-pane web simulator (Parent / Health worker / Facility + CHA) is the demo client. A gateway adapter (Africa's Talking or a county shortcode in Kenya; Twilio elsewhere) is a thin mapping onto this endpoint and is not built.
- **Parent line.** The parent only ever gets one of five fixed English messages: go now, go now (unregistered number), your health worker has been told (with a deadline and the danger-sign list), the health worker did not reply (go now), or not for this number. The parent is never asked a question and never gets advice, reassurance, a diagnosis, a medicine or a dose. A send-time check refuses any other text to a parent.
- **Health-worker line.** Deterministic: a regex and a fixed keyword list read the text for signs that are present; nothing is ever read as absent. The health worker gets the full 8-option checklist and only a numbered reply ("0") clears a sign. Any sign, "9", silence or two unreadable replies refer.
- **Case board.** In the health-worker pane: her cases with code, age, a danger flag, the signs recorded, status (to check / referred / no reply / arrived / closed) and time, danger first, then oldest. Built only from stored case records; nothing generated. After an arrival it shows "follow-up visit due {date}", after she closes a case with "0" "check on child due {date}" (3 days, WHO/UNICEF CHW manual pp.98 and 116); these say only when to go back and are never sent as SMS.
- **Referral loop.** Every referral sends an alert with a 4-digit code to the facility and the community health assistant (CHA). The facility texts the code on arrival; the health worker and CHA are told the child arrived. The facility owns the arrival code. No reply to a code means it was not recorded: resend.
- **Rules.** `config/protocol.yaml` holds the RED (refer) rules from the WHO/UNICEF community case management materials, editable by the ministry. Must-stay-RED tests (T1 to T35, T34 retired) and caregiver tests (CG1 to CG18, CG16 retired) run on every load: a protocol edit that drops a RED rule is refused, and any red caregiver test switches the parent door off.

## Runs on a phone-class device

The model runs on the health worker's own phone, with no internet or data bundle; SMS is the only channel. Where her phone fails, the same model runs on a county box behind the SMS number: still no internet, but a shared local server rather than her device. In this demo a Raspberry Pi plays both roles.

> Raspberry Pi 5 (4x Arm Cortex-A76, 8 GB) runs the model here, as a county backup and as a stand-in for the health worker's phone. Phones issued to Kenyan health workers are reported to have 2 GB RAM (chipset not published); entry-level phones sold in Kenya use older Arm cores (Cortex-A55/A75). So we report peak RAM and 1- and 2-core timings. Not yet measured on a phone; no phone app was built this weekend.

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

## Safety contract and preconditions

- Outgoing SMS are English only in this build. Swahili versions are future work and need a native speaker's back-translation, keeping every qualifier, before any use.
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

### Human in the loop

The tool never decides against care. Only a health worker can close a case, and only by replying "0" (none of the danger signs, all checked) after seeing the child. Every other path ends with a person: the health worker is called, the facility and CHA are alerted, and the facility confirms arrival. The model can only add a reason to send a child now; it can never remove one.

### The fail-safe

When the tool is not sure, it sends the child or calls a person; it never guesses "fine". A message it cannot read, a missing age, a silent health worker, a health worker who replies "9" (not sure), a model that fails to load: each one ends in "go now" for the parent or in the health worker being told, with a deadline. If a caregiver safety test fails at start-up, the parent line falls back to a fixed "go to the nearest health facility NOW" reply and the CHA is told; it is never silent.

### Drift and bias monitor

**Drift and bias monitor (DESIGN).** Each case logs the model's flags next to the health worker's checklist answers. A weekly count of disagreements, by sign and by language, goes to the CHA. A rising count means the model is drifting or failing a group of parents, and is the trigger to review it.

## Where the record lands

**Where the record lands (DESIGN, not built).** Each case produces two records: a referral (case code, child's age, CHP, danger signs flagged, time sent) and an arrival (facility, time seen). In a real deployment these would be sent to eCHIS, the Ministry of Health's community health app built on Medic's Community Health Toolkit, which already includes client referral. eCHIS data is reported to sync to KHIS, Kenya's national DHIS2 instance, so counts would roll up there. No public inbound API is confirmed. The demo writes the same fields to a local database.

Sources: Medic, 2023 (https://medic.org/stories/accompanying-kenyas-ministry-of-health/ ; https://medic.org/stories/cht-interoperability-reference-application-adoption-by-ministry-of-health-kenya-to-facilitate-data-exchange/); Living Goods, 16 Oct 2023, sync (secondary) (https://livinggoods.org/media/kenya-takes-bold-step-towards-universal-health-coverage-with-the-launch-of-a-digital-health-tool/); DHIS2.org, 10 Aug 2026 (https://dhis2.org/kenya-launches-dhis2-for-case-based-eye-care-program/).

## Production gaps

- A keyed hash of phone numbers.
- 3-segment delivery on Kenyan basic phones untested.
- Gateway request validation.
- The reply window agreed with the county.
- A health worker may answer the checklist after a phone call only.
- Same age = same child, so twins are a residual.
- An unknown number would get Swahili + English in one SMS in production (future work, needs native review).

## Built during the event

All project code was written after 12:00 ET on Sat 3 Oct 2026. Made before the event and disclosed: planning documents, the pre-registration (`PREREGISTRATION.md`, tag `prereg`) and test set (a) (`tests/caregiver_set_a.csv`, Claude-written test data, commit b492142). `docs/privacy.html` and `docs/terms.html` (SMS privacy policy and terms) were added on 1 Oct for SMS carrier registration and are not project code.

## Changes after pre-registration

- Before sealing, rows D10 and N03 of set (a) were corrected for format (age present; duration clearly over 14 days; no breathing/chest/"worse" words), and Florian saw those two rows' text; the other 23 rows were not read.
- "miaka" added as a year unit on Sat 3 Oct, before any test set was opened; source: the system's pre-event Swahili onboarding text.
- "umri N" without a unit is treated as no age (an age needs a unit).
- **Deployment rule and deployed model.** Extends prereg section 7: deploy the smallest variant with at least 99% go-now agreement with FP32 on Y-dev and no danger message missed that FP32 catches, chosen on Y-dev before `freeze`. Deployed: the v1 model with its vocabulary trimmed after fine-tuning to 9,759 tokens (keep-list: single Latin characters, X train, the keyword lists, the fixed strings, MASSIVE train) and weights stored as 8-bit (weight-only, per channel), 90.3 MB with tokenizer (FP32: 1,074.9 MB). Reason: the brief's rule that model files must be small enough to side-load or send over a weak connection. The registered row stays FP32 as pre-registered (the registered INT8 failed the section 7 rule); the deployed variant is reported as its own labelled row.
- **Rung 3.** The parent line runs the keyword list live; the model was scored on the Pi (single pass, frozen), not used live, because it failed the caregiver safety tests (CG1 and CG5 with the encoder on) and the Y-dev go-live gate (more needless go-nows than the keyword list).
- **v2.** A second training run (v2) added terse and negated messages after the v1 encoder failed the caregiver safety tests CG1/CG5; training on short danger-term messages makes CG1 easier to pass, which we consider legitimate because recognising bare danger terms is what CG1 requires. v2 still failed (CG5, CG5b, CG10, CG12 and the Y-dev gate) and is reported as its own labelled row.
- **Exploratory row (not pre-registered).** MASSIVE sw-KE: human-written Swahili (translated virtual-assistant commands, no health content); tests false alarms only, not danger detection.

## Word lists added on Saturday (from the protocol sources only)

- Under 2 months: "newborn" (S10). Pregnancy and adult words: "pregnant", "pregnancy", "adult".
- Swahili newborn and pregnancy terms: none in the protocol sources; such messages without an age fall to "go now, age not received".
- Duration symptom words: cough, kikohozi; diarrhoea, diarrhea, kuhara; fever, homa. The Swahili words come from the pre-event ASK_SIGNS option 7 ("Siku: kikohozi 14+, kuhara 14+, homa 7+").
- Hedges: "labda", "?". "about a week" and "a week" count as 7 days. Numbers written as words are not read.
- Swahili keyword and test words come from AI-drafted planning text that no native speaker checked.

## Data and evaluation (filled at `freeze` and `results`)

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
