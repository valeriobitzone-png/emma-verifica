#!/usr/bin/env bash
# Scarica Emma-6 da Hugging Face in ./model (i pesi NON sono inclusi in questo repo).
# Modello e licenza (OpenRAIL): https://huggingface.co/egomnia/emma-6
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p model
# 1) Repo ufficiale Egomnia: tokenizer, config e export ONNX INT8 (backend "onnx", lento ma ufficiale)
hf download egomnia/emma-6 --revision 2664c31400e354ac4a6719fce0030a92efe81cce \
  bpe.model config.json tokenizer_config.json emma6_full_config.json README.md README.txt \
  emma6.int8.onnx emma6.int8.onnx.data --local-dir model
# 2) Conversione GGUF Q8_0 di terzi (NON ufficiale Egomnia) usata per i run misurati (backend "gguf", llama.cpp)
hf download PaoloneSborracchione/emma-6-GGUF --revision 00093d9101e5b7a56d234a35bfd40d07f5e0ea54 \
  emma-6-Q8_0.gguf --local-dir model
echo "342a87b85563d07150843fcb403daa8c1515ee855a137ab674d39379552ecfce  model/emma-6-Q8_0.gguf" | sha256sum -c -
