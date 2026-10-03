---
title: SafetyNet-SMS
emoji: 📟
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Child danger-sign SMS triage demo (synthetic data only)
---

# SafetyNet-SMS: public demo

**Demo with synthetic data. Not for medical use.** In deployment this runs offline on the health worker's phone; this public demo runs the same code on a cloud server so you can try it.

- Built from the GitHub repo at tag `submission`: https://github.com/ranbirdaefler/SafetyNet-SMS
- Board model: https://huggingface.co/ranbirr1/safetynet-sms-board (v3, 92.7 MB, SHA-256 checked at start-up)
- No SMS gateway is connected. Phone numbers, health workers and villages are fictional. Facility names: © OpenStreetMap contributors (healthsites.io, ODbL).
- Cases reset after 30 minutes of inactivity, or with "Reset demo".
