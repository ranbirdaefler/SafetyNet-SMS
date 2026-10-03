# Pre-registration: SafetyNet-SMS

Written Friday 2 October 2026, before the hackathon starts (12:00 ET, Saturday 3 October 2026).

**Commit order.** Set (a) is committed alone first. This file is committed next, citing set (a)'s commit and SHA-256, and that commit is tagged `prereg`. The evidence for the time is GitHub's push record. Nothing in this file changes after the `prereg` push. Any later change is listed in the README under "Changes after pre-registration", with the reason.

## 1. What is compared

SafetyNet-SMS reads a parent's free-text SMS about a sick child (2 to 59 months) and replies with one of five fixed English messages. It either tells the parent to take the child to the facility now ("go now"), or tells them their health worker has been told, with a deadline and the danger-sign list.

Two extractors are compared inside the same parent-policy function, the one the live service uses:
- **The encoder:** AfroXLMR-base with 8 yes/no heads, fine-tuned during the event on GPT-written training text (section 7).
- **The keyword list:** a frozen list built from the hand-written word lists in section 5 plus n-grams mined from the training text by the fixed recipe in section 5.

Everything else is identical in both arms:
- the age and duration regex;
- the C4 list (breathing and "worse");
- the shared stage for chest, MUAC and feet;
- the scope rules (under 2 months, 5 years and over, pregnancy, adult, no age).

## 2. The claim (verbatim)

> "On the native-speaker caregiver messages sealed unread before the freeze, the encoder's sensitivity for messages containing a danger sign ('go now' triggered) is not lower than the frozen keyword list's, and its false 'go now' rate on messages with no danger sign is lower (exact McNemar test, two-sided p < 0.05)."

**Status at registration:** no native-speaker test set exists, and no human-written test set exists. Every results table and the video carry the header **"Pre-registered claim (native Swahili): NOT TESTED"**. The only exception is a native set of 20 or more messages committed unread before the `freeze` push (section 3).

## 3. Test sets and data families

**Circularity control.** Training data (X) and the development set (Y-dev) come from **GPT** (OpenAI) only. **All test sets come from Claude** (Anthropic): set (a), set (b) and Y-test. The encoder never trains or tunes on Claude-written text. No Gemini data is used.

**What this does not control:**
- Every test message is written by an AI model, so none of the results show performance on real parents' texts.
- The Swahili words in the keyword list (section 5) come from planning text that was drafted with Claude and never checked by a native speaker. The keyword list and every test set therefore share a source, and this favours the keyword list.
- Y-dev is from the same family as the training data, so the go-live gate and k are set on text that is easier for the encoder than the test sets are.

| Set | Written by | When | Size: danger / no-danger / shared path | Label in tables |
|---|---|---|---|---|
| **(a)** | Claude Opus 5.5, in a fresh chat with no access to the project spec or any keyword list, from the D/N grid below | Fri 2 Oct, before this file | 25: 12 / 13 / 0 (planned by the grid) | "(a) Claude-written from a fixed case grid" |
| **(b)** | Claude (claude-opus-5-5), Swahili caregiver messages from the same D01 to D12 and N01 to N13 grid as set (a) | Sat 3 Oct at 12:00, before any model or keyword-list code; committed unopened | 25: 12 / 13 / 0 (planned by the grid) | "(b) AI-generated Swahili (claude-opus-5-5), not checked by a native speaker" |
| **Y-test** | Claude (claude-opus-5-5), caregiver voice | Sat 3 Oct, in-event; committed unopened | 150: 80 / 55 / 15 | "Y-test, Claude, caregiver" |
| Native (conditional) | A native Swahili speaker (Fiverr job) | Counts only if committed unread before the `freeze` push | 25 | The claim row if 20 or more; 1 to 19 is a separate row, "native, partial ({n} of 25), claim not tested" |
| Y-dev (not a test set) | GPT (gpt-5.5) | Sat 3 Oct | 120: 60 / 45 / 15 | "dev"; used for the go-live gate, k and the INT8 rule only |
| X train (not a test set) | GPT (gpt-5.5) | Sat 3 Oct | 1,200 (cut line 600) | |

**Set (a) details:**
- **File:** `tests/caregiver_set_a.csv`, with columns `id,label_line,message`; " || " separates the two texts of a two-text row.
- **Commit:** `b49214293144da61c9229a4c8596072c7178411f`.
- **SHA-256 of the committed file:** `9196368a1809840112cab985ea9564a5b9cbe1ce63d0145484d0cde7ab4ae835`. This was computed from the working copy before commit (LF line endings, 26 lines including the header) and must equal `git show <commit>:tests/caregiver_set_a.csv | sha256sum`.
- **Builder read the messages:** no (the builder did not open the file before this commit). The hand-written word lists in section 5 were fixed on 1 October, before set (a) was written. The n-gram recipe uses training text only.

**Labels** come from the grid ID and the label line (D = danger, N = no-danger) or the card, never from the message text.

**Set (a) and set (b) grid** (set (a) was written from it; set (b) is written from it on Saturday):
- **Danger (12):**
  - D01 convulsions; D02 the same, described, hedged;
  - D03 cannot drink or feed; D04 the same, negative form, 2 texts;
  - D05 vomits everything; D06 the same, described;
  - D07 very sleepy; D08 "hard to wake", hedged;
  - D09 blood in stool, 2 texts;
  - D10 cough 14+ days, relative time; D11 fever "about a week"; D12 diarrhoea 3 weeks.
- **No danger (13):**
  - negated: N01 fits, N02 blood, N03 sleepy, N04 drinking;
  - near-miss: N05 vomits but drinks, N06 sleepy but wakes and feeds, N07 fever 5 days, N08 cough 10 days, N09 diarrhoea 4 days (2 texts), N10 eats less but drinks;
  - plain: N11 fever 2 days, N12 rash, N13 runny nose.

**Late sets:** a set counts if its unopened commit is pushed before the `freeze` push. A set pushed after it is not run. Counts are git's insertion counts at the commit, so the file is never opened to count it.

## 4. Order of operations and blinding

1. Commit set (a) alone; commit this file; tag `prereg`; push.
2. **Saturday from 12:00 ET:**
   - generate X train and Y-dev (GPT), and Y-test and set (b) (Claude);
   - commit the test files unopened;
   - stage test files with `git add` only, and never open, diff or view them.
3. Build the service. v0 of the keyword list is typed from section 5. E2 is mined from X train by the section 5 recipe.
4. **Go-live gate on Y-dev** (section 9), then the INT8 decision (section 7). Then push the `freeze` tag. The `freeze` commit records the commit IDs and line counts of every set, k, the keyword list, the gate outcome, the model IDs, FP32 or INT8, and the model file's `git hash-object`. Model weights stay out of git.
5. Start the test runs on every set committed before the `freeze` push. Runs write raw output files and print a file count only.
6. **After sleep:** run the metric code on Y-dev, commit and push it, then open the test outputs and fill the tables (tag `results`). No table code touches a test set before the metric code is pushed.
7. Fixes found after that are labelled post-hoc. The frozen numbers stay primary.

## 5. Keyword lexicon and shared word lists (fixed now)

One keyword list serves the health-worker line, the parent-line fallback and the comparator. **No word is added or removed by hand after this commit.** The words below were fixed on 1 October and are copied without change. The Swahili was drafted with AI and never checked by a native speaker.

**Danger terms (T-list):**

| Row | English | Swahili |
|---|---|---|
| R5 convulsions | convulsion, convulsions, fits | degedege |
| R6 cannot drink or feed | cannot drink, cannot feed, cannot breastfeed, not able to drink, unable to drink | hawezi kunywa, hawezi kunyonya, hanyonyi, kushindwa kunywa, kushindwa kunyonya |
| R7 vomits everything | vomits everything, vomiting everything, nothing stays down | anatapika kila kitu, kutapika kila kitu |
| R9 unusually sleepy or unconscious | very sleepy, unusually sleepy, hard to wake, cannot wake, cannot be woken, unconscious | usingizi mwingi, usingizi usio kawaida, usingizi usio wa kawaida, haamki |
| R3 blood in stool | blood in stool | damu kwenye kinyesi |
| R8 chest indrawing (shared stage) | chest indrawing | kifua kinaingia, kifua kuingia ndani |
| R10, R11 MUAC red, feet (shared stage) | muac red, both feet swollen, dent stays on both feet | muac nyekundu, miguu yote imevimba |

R1 (cough 14+ days), R2 (diarrhoea 14+ days) and R4 (fever 7+ days) come only from the duration regex, never from words, so "homa" (fever) alone never fires.

**Normalisation:** lowercase; "can't", "cant" and "can not" become "cannot".

**Negation cues (closed list of 20):** no, not, never, without, isn't, isnt, doesn't, doesnt, didn't, didnt, hasn't, hasnt, don't, dont, hana, hakuna, hajawa, hajapata, bila, wala. "si" and "sio" are not cues. A cue makes a sign OPEN (not read), never absent.

**Never-negated phrases:** a match containing any of these is never negated: cannot drink, cannot feed, cannot breastfeed, not able to drink, unable to drink, cannot wake, cannot be woken, nothing stays down, hawezi kunywa, hawezi kunyonya, hanyonyi, kushindwa kunywa, kushindwa kunyonya, haamki.

**Matching:**
- The longest phrase wins, and tokens inside a match never act as cues.
- A cue counts only within k tokens before the sign, in the same clause. Cues after a sign do not count.
- A clause ends at , . ; : ? ! a line break, ||, "lakini", "ila" or "but".
- A negated match is OPEN.

**C4 list (breathing and "worse"; a match means go now):** breathing, breath, chest | anapumua, pumzi, kifua; worse, sicker. It ignores negation, gets no mined n-grams and runs the same in both arms. There is no Swahili "worse" word, so a Swahili report of worsening is not read as go-now.

**Shared stage (chest, MUAC, feet):** the R8, R10 and R11 rows above plus the MUAC regex. It ignores negation, runs the same in both arms, and has no encoder head. A chest match is reported as "breathing complaint".

**Shared age and duration regex (both arms).** The rules fixed now are listed below. Any word added on Saturday must come from the protocol sources, never from a test set or the training text, and is listed in the README.
- An age needs a unit. Units named in the planning record: m, months, y, years, d, days, weeks; miezi, mwezi, mwaka, wiki, umri, siku.
- "wiki N" counts as 7N days.
- A range takes its upper bound.
- "about a week" counts as 7 days. A hedged count at the threshold counts as present.
- MUAC is read from 50 to 300 mm or 5.0 to 30.0 cm; under 115 mm is red.
- **Under 2 months** means under 60 days, under 9 weeks or under 2 months. Exactly 2 months is in scope.
- **Newborn, pregnancy, adult and hedge word lists** are written on Saturday from the protocol sources only, before any test set is opened, and listed in the README.

**v0** (typed on Saturday) = the T-list sign rows plus the cues, with k = 2.

**E2** (built on Saturday after X train exists) = the T-list sign rows plus mined n-grams:
1. Tokens are lowercased and split on spaces and on punctuation except apostrophes. Clause breaks are as above, including the join between the two parts of a two-text message.
2. Candidates for sign s are 1- to 3-grams within one clause, with no digits, from deduplicated X-train messages whose label has s present.
3. pos = messages labelled s with a non-negated occurrence (no cue within 3 tokens before it in the same clause). tot = all messages with a non-negated occurrence.
4. Keep a candidate if pos ≥ 5 and pos/tot ≥ 0.90. Drop any n-gram that is, or contains, a cue. Rank by precision, then pos, then fewer tokens, then alphabetical. Keep the top 20 per sign (R3, R5, R6, R7, R9 only). These thresholds are fixed and never tuned.
5. R8, R10 and R11 get T-list terms only. The C4 words stay in the C4 list only.
6. **k for E2** = the widest window from 0 to 5 tokens that negates no present instance on Y-dev. k = 0 is reported as "keyword list without negation".
7. E2 runs live only if all must-stay-RED tests pass with it loaded; otherwise v0 runs live. **E2 is the comparator either way.**

## 6. Fixed message details

- **Reason words** (in this order: signs, C4, scope, system):
  - signs, as the checklist's short labels: "convulsions", "cannot drink or feed", "vomits everything", "very sleepy or cannot wake", "chest indrawing", "blood in stool", "long illness", "MUAC red or swelling of both feet";
  - C4: "breathing complaint", "parent says worse";
  - scope: "age not received", "under 2 months".
  - A chest reading from a parent's text is named "breathing complaint", never "chest indrawing".
- **{time}** is HH:MM on a 24-hour clock. It is the event time in ALERT, ACK and ARRIVED, and the due time in CG_TOLD and CHP_CALL.
- **CHU and CHP codes** appear as "CHU 3" and "CHP 07".
- **A message sent in two parts** carries the suffix " (1/2)" and " (2/2)".
- **Generation prompts** are committed on Saturday before any generation call. They are not part of this pre-registration.

## 7. The encoder

- **Model:** AfroXLMR-base with 8 yes/no heads (convulsions, not_drink_feed, vomits_everything, sleepy_unconscious, blood_stool, cough_long, diarrhoea_long, fever_long).
- **Training labels:** an 8-bit present vector from the card. Absent, not mentioned and not measured are all 0. Hedged and negative-form mentions are labelled present.
- **Recipe (one run):** binary cross-entropy, no class weights, learning rate 3e-5, bf16, 3 epochs, max length 256 tokens (above 256: the first and last 256 tokens, present in either counts).
- **Present rule:** a sign is present when its head gives p ≥ 0.5, one value for all 8 heads, never tuned. Below 0.5 means OPEN, never absent.
- **Encoder findings can only add a go-now reason.** They are OR-ed with the regex, C4 and the shared stage and never remove a reason those give. Age comes from the regex only.
- **Runtime:** ONNX Runtime on a Raspberry Pi 5 8 GB, live during the event. **FP32 is the default.**

**INT8 rule:** INT8 (dynamic quantization of MatMul only) is used only if, on Y-dev, both of these hold:
- it agrees with FP32 on at least 99% of go-now decisions (with 120 messages, at most 1 disagreement);
- it misses no danger message that FP32 catches.

Otherwise FP32 is used. The `freeze` commit records which one ran, and the results tables say so.

**Engineering bar:** peak RSS ≤ 3 GB on the 8 GB Pi; p95 ≤ 300 ms per 64-token message.

**Measured on Friday 2 October** (afro-xlmr-base ONNX, untrained heads, 4 threads, 64 tokens, 50 runs; weights deleted afterwards):

| | Load | p50 | p95 | Peak RSS |
|---|---|---|---|---|
| FP32 | 1.4 s | 124 ms | 125 ms | 2,132 MB |
| INT8 | 0.5 s | 45 ms | 47 ms | 790 MB |

- FP32 ONNX outputs matched PyTorch exactly.
- The INT8 CLS embedding had a cosine similarity of 0.867 with FP32.
- 200-token latency and tokenizer parity between the Pi and the desktop were not measured before registration.

## 8. Definitions and decision rules

- **Unit:** one message ID. For a two-text row, go-now on either text counts. Both arms read the same messages, each read once (single pass); the dialogue is not replayed.
- **Danger message:** its label lists convulsions, cannot drink or feed, vomits everything, very sleepy, blood in stool, cough 14+ days, fever 7+ days or diarrhoea 14+ days (hedged counts). **No-danger message:** none of these, age 2 to 59 months.
- **Triggered:** the parent-policy function returns "go now" with a sign, a C4 word or "under 2 months" among its reasons. A go-now whose only reason is "age not received" does not count as triggered; it gets its own column per arm. Every message is scored as coming from a registered sender whose health worker is idle.
- **Sensitivity** = triggered danger messages / danger messages. **False go-now rate** = triggered no-danger messages / no-danger messages.
- **"Not lower":** encoder misses ≤ keyword-list misses, as point counts with no margin.
- **"Lower":** on no-danger messages, b = sent needlessly by the keyword list only, c = sent needlessly by the encoder only; exact two-sided McNemar test, p < 0.05. With 10 no-danger messages a win needs 6:0 or better, or 8:1 or 9:1.
- **Per-arm rates** are shown with Clopper-Pearson 95% intervals.
- **What these sizes can show:** zero misses still allows a true miss rate up to 28.5% of 11, 26.5% of 12 and 4.5% of 80. One and two misses of 11 allow up to 41.3% and 51.8%. Zero, one and two false go-nows of 10 allow up to 30.8%, 44.5% and 55.6%. These results guard against a worse encoder; they are not a safety certificate.
- **Shared-path messages** (under 2 months, breathing complaint, no age) are left out of both denominators, because the shared rules trigger them in both arms. They are reported as n of s per arm and are expected to be s of s. A shortfall is a bug: listed as a missed go-now, fixed and labelled post-hoc, with the outcome unchanged. A {c4} column counts danger messages where the C4 list fired.
- **Baselines:** two fixed rows, "always go now" and "never go now". An arm with misses + needless ≥ min(danger count, no-danger count) is flagged "no better than a fixed rule".

## 9. Go-live gate and the safety switch

- **Go-live gate** (Y-dev, on the Pi): encoder misses ≤ keyword-list misses, encoder needless go-nows ≤ the keyword list's, shared path complete, p95 within budget. If it fails, the keyword list runs the parent line live and the encoder is reported as a table row only.
- **Safety switch (checked first, on every test set shown):** if the encoder misses more danger messages than the keyword list on any test set, the keyword list runs the parent line in the demo, and the video says so. A win cannot coexist with a switch.

## 10. Outcomes and video lines

Checked in this order: the safety switch, then Win, then Tie-or-loss. **"No native set" is the expected outcome.** In the lines below, {x}, {y} and {f} are counts, filled from the frozen tables.

**No native set (fewer than 20 native messages committed before the freeze):**

> "No native speaker's texts were sealed in time, so my registered claim is not tested. On three stand-in sets, the model sent {x_a} of 12 children with a danger sign to the clinic in 25 test messages an AI model wrote from a fixed case grid, {x_b} of {m_db} in 25 AI-written Swahili texts no native speaker checked, and {x_yt} of 80 in {N_yt} AI-written test texts; the keyword list {y_a}, {y_b}, {y_yt}. Needless trips: model {f_a} of 13, {f_b} of {m_nb}, {f_yt} of 55; keyword list {f_a_lex}, {f_b_lex}, {f_yt_lex}. None are real parents' texts, so the model is not shown to beat a keyword list."

On screen with it: "Test messages written by an AI model from a fixed case grid; no native or human-written test set."

If a partial native set (1 to 19) exists, the first sentence becomes: "Only {n} of 25 texts from a native speaker were sealed in time, too few to test my registered claim."

**Win (20 or more native messages; no switch; p < 0.05):**

> "On {N_cg} parents' texts written by a native Swahili speaker, the model sent {x} of {m_d} children with a danger sign straight to the clinic (keyword list {y}) and only {f} of {m_n} without one (keyword list {f_lex}); with this few texts a miss rate up to {u}% is still possible."

**Tie-or-loss (20 or more native messages; not a win):**

> "On {N_cg} parents' texts the model and a keyword list missed {k} and {k_lex} of {m_d} children with a danger sign and sent {f} and {f_lex} of {m_n} others needlessly, so the model is not shown better; the value is the route: parent, health worker, clinic, arrival confirmed."

**Safety switch** (it replaces the Win or Tie-or-loss line; with no native set it is added after the paragraph above):

> "Before testing I set a rule that the model may not miss more children with a danger sign than a keyword list; on {set} it missed {k} of {m_d}, the keyword list {k_lex}, so the keyword list now runs the parent line."

## 11. Results tables

There is one table per set, never pooled.
- **Header:** "Single pass: each message read once, first reply scored; dialogue not replayed. Registered senders only. Ours = {FP32 or INT8} ONNX on the Pi 5 (8 GB)."
- **Rows:** always go now; never go now; keyword list (E2); ours.
- **Columns:** missed go-now (with CP 95%); needless go-now (with CP 95%); shared path n of s; {c4}; "age not received" alone; Pi p95.
- Below each table: the discordant no-danger counts (b, c) and the exact McNemar p.
- **Error listing:** every error by message ID, with its class (lay wording, negation, hedging, temporal, code-mixing, typo, split, generator error).

## 12. Expected outputs (clinical safety)

- **A breathing complaint:** "go now" to the parent; the health worker and facility messages read "PARENT SMS: breathing complaint", never "chest indrawing"; in both arms.
- **A message with no age:** "go now" to the parent, with "age not received" to the health worker and in the facility alert. It goes in the "age not received" column and is not counted as triggered.

## 13. Disclosures this registration commits to (README and video)

- "Pre-registered claim (native Swahili): NOT TESTED", unless a native set of 20 or more counts.
- "Test messages written by an AI model from a fixed case grid; no native or human-written test set."
- "Training and development data were written by GPT; every test set was written by Claude."
- "The keyword list's Swahili words and the test sets both come from Claude-written text; this favours the keyword list."
- "Swahili keyword and test words come from AI-drafted planning text that no native speaker checked."
- "Outgoing SMS are English only in this build. Swahili versions are future work and need a native speaker's back-translation, keeping every qualifier, before any use."
- "A parent message without the child's age is sent to the facility at once; this over-refers on purpose."
- "A Swahili report that the child is worse is not read as go-now; the parent still gets the deadline and the health worker is called."
- "A negation before another word can hide a sign; the parent still gets the danger-sign list and the deadline."
- "Swollen feet in other words do not send the parent at once; the health worker is called and answers the full checklist, which asks about both feet (option 8)."
- "Y labels not hand-checked."
- "No text is ever read as absent; only a numbered reply clears a sign. Enforced by must-stay-RED tests on every load; not counted on the test sets."
- "Numbers not in the registry are always sent to the facility; in production the health worker would add the number at household registration."
- Which keyword list ran live (E2, or v0 if E2 failed a must-stay-RED test), and FP32 or INT8.
- "SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway. Everything behind the gateway runs as shown, on this Pi."
- "Not clinically validated."
