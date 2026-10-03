# SafetyNet-SMS

**Pre-registered claim (native Swahili): NOT TESTED**

A parent texts a free-text SMS about a sick child (2 to 59 months) in Swahili, English or both. A box in the county (a Raspberry Pi 5) reads it for danger signs and either tells the parent to take the child to the facility now, or tells them their health worker has been told, with a deadline and the danger-sign list. The health worker gets a fixed checklist; the facility gets an alert with a code and texts the code back when the child arrives.

World Bank / Hack-Nation *Small AI for Development* hackathon, health track, 3 to 4 October 2026.

> SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway. Everything behind the gateway runs as shown, on this Pi. Synthetic cases; not clinically validated.

## How it works

- **One endpoint.** `POST /sms {from, to, body}`; the role (parent, health worker, facility) comes from the number texted. A 3-pane web simulator (Parent / Health worker / Facility + CHA) is the demo client. A gateway adapter (Africa's Talking or a county shortcode in Kenya; Twilio elsewhere) is a thin mapping onto this endpoint and is not built.
- **Parent line.** The parent only ever gets one of five fixed English messages: go now, go now (unregistered number), your health worker has been told (with a deadline and the danger-sign list), the health worker did not reply (go now), or not for this number. The parent is never asked a question and never gets advice, reassurance, a diagnosis, a medicine or a dose. A send-time check refuses any other text to a parent.
- **Health-worker line.** Deterministic: a regex and a fixed keyword list read the text for signs that are present; nothing is ever read as absent. The health worker gets the full 8-option checklist and only a numbered reply ("0") clears a sign. Any sign, "9", silence or two unreadable replies refer.
- **Referral loop.** Every referral sends an alert with a 4-digit code to the facility and the community health assistant (CHA). The facility texts the code on arrival; the health worker and CHA are told the child arrived. The facility owns the arrival code. No reply to a code means it was not recorded: resend.
- **Rules.** `config/protocol.yaml` holds the RED (refer) rules from the WHO/UNICEF community case management materials, editable by the ministry. Must-stay-RED tests (T1 to T35, T34 retired) and caregiver tests (CG1 to CG18, CG16 retired) run on every load: a protocol edit that drops a RED rule is refused, and any red caregiver test switches the parent door off.

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

**Where the data sits.** Every message, case and timer is stored in one SQLite file on the county box (the Pi, `data/sms.db`). No cloud model is called at decision time; the model runs on the box. Nothing leaves the box except the SMS replies themselves. In deployment the box sits with the county health team, so primary-care data is processed in Kenya.

**Who can read it.** Only whoever administers the county box can read the database. The health worker sees only the messages sent to their own phone; the facility and CHA see only alerts with a case code, the child's age and the reasons, never a name and never the parent's own words. The parent's phone number appears only in the five messages that ask the health worker or CHA to call the parent. The demo uses synthetic numbers only.

**When a phone is lost or shared.** No SMS carries a name, a diagnosis or a medicine, so a lost or shared phone shows a case code, an age, the danger signs reported and an instruction to go to the facility. A parent message from an unknown number (a borrowed phone, a new SIM) is never turned away: it gets "go to the nearest facility now", and the CHA is told. A health-worker number that is not registered gets no case information at all. A lost health-worker phone is removed from the registry by the county; open cases then time out to "go now" for the parent.

**Human in the loop.** The tool never decides against care. Only a health worker can close a case, and only by replying "0" (none of the danger signs, all checked) after seeing the child. Every other path ends with a person: the health worker is called, the facility and CHA are alerted, and the facility confirms arrival. The model can only add a reason to send a child now; it can never remove one.

**The fail-safe.** When the tool is not sure, it sends the child or calls a person; it never guesses "fine". A message it cannot read, a missing age, a silent health worker, a health worker who replies "9" (not sure), a model that fails to load: each one ends in "go now" for the parent or in the health worker being told, with a deadline. If any safety test fails at start-up, the parent line switches off rather than run untested.

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
