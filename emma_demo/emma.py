"""Wrapper di generazione per Emma-6.

Due backend, stesso prompt e stesse impostazioni (greedy):
- "gguf": llama.cpp su conversione GGUF Q8_0 (veloce, con KV cache) -- usato per i run.
- "onnx": export ufficiale Egomnia emma6.int8.onnx (nessuna KV cache: lento) -- usato per la verifica di coerenza.
"""
from __future__ import annotations
import os, time
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
STOP = ["\nUtente:", "\nEmma:"]


def build_prompt(user_msg: str) -> str:
    # Formato usato dallo Space pubblico Radonia/emma-6-chat
    return "\nUtente: " + user_msg.strip() + "\nEmma:"


class EmmaGGUF:
    def __init__(self, path: str | None = None, n_threads: int | None = None):
        from llama_cpp import Llama
        path = path or os.environ.get("EMMA_GGUF") or str(MODEL_DIR / "emma-6-Q8_0.gguf")
        self.llm = Llama(model_path=path, n_ctx=4096, n_threads=n_threads or os.cpu_count(),
                         n_batch=512, verbose=False, seed=0)

    def generate(self, prompt: str, max_tokens: int = 96) -> tuple[str, float]:
        t = time.time()
        out = self.llm.create_completion(prompt=prompt, max_tokens=max_tokens, temperature=0.0,
                                         top_k=1, stop=STOP, repeat_penalty=1.1)
        return out["choices"][0]["text"].strip(), time.time() - t

    def generate_until(self, prompt: str, done, max_tokens: int = 96) -> tuple[str, float]:
        """Come generate(), ma in streaming: si ferma appena done(testo_parziale) è vero.
        Latenza: la pipeline usa solo la prima frase utile, i token successivi erano sprecati."""
        t = time.time(); text = ""
        it = self.llm.create_completion(prompt=prompt, max_tokens=max_tokens, temperature=0.0, top_k=1,
                                        stop=STOP, repeat_penalty=1.1, stream=True)
        for ch in it:
            text += ch["choices"][0]["text"]
            if done(text):
                it.close(); break
        return text.strip(), time.time() - t


class EmmaONNX:
    def __init__(self):
        import onnxruntime as ort, sentencepiece as spm
        so = ort.SessionOptions(); so.intra_op_num_threads = os.cpu_count()
        self.sess = ort.InferenceSession(str(MODEL_DIR / "emma6.int8.onnx"), so,
                                         providers=["CPUExecutionProvider"])
        self.sp = spm.SentencePieceProcessor(model_file=str(MODEL_DIR / "bpe.model"))

    def generate(self, prompt: str, max_tokens: int = 48) -> tuple[str, float]:
        import numpy as np
        t = time.time()
        ids = [2] + self.sp.encode(prompt)
        start = len(ids)
        for _ in range(max_tokens):
            logits = self.sess.run(None, {"input_ids": np.array([ids], dtype=np.int64)})[0]
            nxt = int(logits[0, -1].argmax())
            if nxt == 3:
                break
            ids.append(nxt)
            text = self.sp.decode(ids[start:])
            if any(s in text for s in STOP):
                break
        text = self.sp.decode(ids[start:])
        for s in STOP:
            text = text.split(s)[0]
        return text.strip(), time.time() - t
