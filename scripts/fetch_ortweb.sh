#!/bin/sh
# Fetch onnxruntime-web 1.30.0 for the /phone page and verify the tarball against npm's published integrity hash.
set -e
mkdir -p sim/ort /tmp/ortweb
cd /tmp/ortweb
curl -sL -o ortweb.tgz https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-1.30.0.tgz
want=$(curl -s https://registry.npmjs.org/onnxruntime-web/1.30.0 | python -c "import sys,json; print(json.load(sys.stdin)['dist']['integrity'].split('-',1)[1])")
got=$(openssl dgst -sha512 -binary ortweb.tgz | openssl base64 -A)
[ "$want" = "$got" ] || { echo "onnxruntime-web integrity mismatch"; exit 1; }
tar xzf ortweb.tgz
cp package/dist/ort.wasm.min.mjs package/dist/ort-wasm-simd-threaded.wasm package/dist/ort-wasm-simd-threaded.mjs /app/sim/ort/
