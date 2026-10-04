---
title: SafetyNet-SMS
emoji: 📟
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Danger-sign SMS assistant for health workers, synthetic data
---

# SafetyNet-SMS: public demo

**Demo with synthetic data. Not for medical use.** In deployment it is designed to run offline on the health worker's phone or a county box; this public demo runs the same code on a cloud server so you can try it. Automatic replies to parents come only from fixed rules. The model never sends anything to a parent on its own: a question it suggests reaches a parent only after the health worker approves it (experimental).

- Built from the GitHub repo at a tagged release (Space variable REF; the final one is the `submission` tag): https://github.com/ranbirdaefler/SafetyNet-SMS
- Board model: https://huggingface.co/ranbirr1/safetynet-sms-board (v3, 92.7 MB, SHA-256 checked at start-up)
- No SMS gateway is connected. Phone numbers, health workers and villages are fictional. Facility names: © OpenStreetMap contributors (healthsites.io, ODbL).
- Cases reset after 30 minutes of inactivity, or with "Reset demo".
