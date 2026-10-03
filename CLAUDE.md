# SafetyNet-SMS — build agent instructions

You are the **build agent** for SafetyNet-SMS, Florian's solo entry to the World Bank / Hack-Nation *Small AI for Development* hackathon (health track). Window: **Sat 3 Oct 12:00 ET → Sun 4 Oct 09:00 ET**. You write the code; Florian reviews, runs things on the Pi, and records the video. A separate planner chat makes design decisions.

## Sources of truth (read before each block)
- `PREREGISTRATION.md` (this repo, tag `prereg`) — **binding**. The claim, test sets, blinding order, word lists, encoder recipe, gate, outcomes, disclosures. Never edit it; deviations go in README "Changes after pre-registration".
- Planning docs in `C:\Users\avsd8\OneDrive\Desktop\hackathon-quorum\quorum\final\`:
  - `WEEKEND_PLAN.md` — block order (B0…B24), times, cut lines, tags.
  - `SPEC.md` — architecture, rules (RED YAML), caregiver-door safety conditions C1–C12, fixed messages, model, data, evaluation, demo.
  - `PITCH.md` — video shots and captions.
- If PREREGISTRATION and SPEC disagree, PREREGISTRATION wins. If something is undefined, ask Florian; don't invent clinical wording.

## Hard rules
1. **Blinding.** Never open, print, read or sample test-set message text (set (a) `tests/caregiver_set_a.csv`, set (b), Y-test, any native file) before the `freeze` tag is pushed, and never before the metric code is pushed (prereg §4). Loaders may read them only inside the frozen harness; runs print counts only.
2. **Seal on arrival.** Generated test sets (b, Y-test) are written to file and committed + pushed **unopened** as soon as generation finishes.
3. **Data families.** Training (X) and Y-dev: GPT `gpt-5.5` only. Test sets (b, Y-test): Claude `claude-opus-5-5` only. Never mix.
4. **Safety (G3).** Parents only ever receive the fixed caregiver messages (CG_GO_NOW, CG_GO_NOW_U, CG_TOLD, CG_TIMEOUT, CG_OOS). No advice, reassurance, diagnosis, medicine or dose anywhere. A caregiver's "absent" never lowers urgency. Must-stay-RED (T1–T35) and CG1–CG18 tests run on every load; a failing test blocks go-live.
5. **Secrets.** API keys only in `.env` (gitignored). Never print or commit them.
6. **Transport.** No Twilio. One generic endpoint `{from, to, body}` → replies; role from `to`. The 3-pane simulator (Parent / Health worker / Facility) is the demo client. Caption: "SMS gateway simulated. In deployment: a county shortcode on a Kenyan SMS gateway. Everything behind the gateway runs as shown, on this Pi."
7. **Hardware.** Raspberry Pi 5, 8 GB, at 192.168.1.208 (user/host FloFlo), CPU-only ONNX Runtime, 4 threads. Training on the desktop RTX 4070 Ti SUPER. Model: AfroXLMR-base (fallback -small), FP32 ONNX default; INT8 (MatMul-only) only by the prereg rule.
8. **Outgoing SMS: messages to health workers, facilities and the CHA are English only. Parent messages: CG_GO_NOW, CG_GO_NOW_U, CG_TIMEOUT and CG_OOS are bilingual, Swahili first, English below as the authoritative line. CG_TOLD is sent in the parent's registered language (Swahili by default, or English). All parent texts are fixed strings approved by Florian; nothing generated is ever sent to a parent.** Input may be Swahili / English / mixed.

## Working loop
- Work block by block in `WEEKEND_PLAN.md` order. At the start of a block, state its goal and "done when" test in one line; at the end, run the test, commit, push, and report in ≤ 5 lines: done / not done, test result, time used vs. budget, anything Florian must decide.
- Build the **thin end-to-end slice first** (simulator → endpoint → rules → reply → alert → arrival) before training. Tag `slice-chw`, `slice`, `mvs`, `freeze`, `results` exactly as the plan says.
- If a block overruns its cut-line time, apply the cut line, say so, and move on. Never cut sleep (01:15–04:15) or the 06:00 recording lock.
- Small commits, clear messages. Keep the README "Built during the event" and disclosure sections current as you go.
- Write `STATUS.md` at repo root after each block (time, current block, last tag, open issues, next step) so the planner chat can read progress.
