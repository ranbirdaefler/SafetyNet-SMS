# SafetyNet-SMS public demo (Hugging Face Space, Docker, CPU basic).
# Runs one fixed commit or tag of the GitHub repo (Space variable REF; `submission` once that tag exists): no fork,
# no rewrite. Fictional data; no SMS gateway.
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends git curl ca-certificates && rm -rf /var/lib/apt/lists/*
ARG REPO=https://github.com/ranbirdaefler/SafetyNet-SMS
ARG REF=submission
RUN git clone ${REPO} /app && cd /app && git checkout --detach ${REF} && git log -1 --format="built from %H"
WORKDIR /app
RUN pip install --no-cache-dir -r requirements-demo.txt
# onnxruntime-web for the /phone page, from the npm registry tarball, checked against its published SHA-512 integrity
RUN sh scripts/fetch_ortweb.sh
RUN mkdir -p /app/models /app/data && chmod -R 777 /app/models /app/data
ENV SNS_PUBLIC=1 SNS_DB=/tmp/sms.db SNS_MODEL=/nonexistent TZ=EAT-3
EXPOSE 7860
CMD python scripts/fetch_model.py && python -m uvicorn app.server:app --host 0.0.0.0 --port 7860 --no-access-log
