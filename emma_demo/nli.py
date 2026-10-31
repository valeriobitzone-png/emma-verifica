"""Verifica di implicazione (NLI) multilingue: la frase di Emma è implicata dal passaggio?
Modello: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (~280M, CPU, ~50 ms a coppia)."""
from __future__ import annotations
import os
from functools import lru_cache

MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"


@lru_cache(1)
def _load():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    torch.set_num_threads(int(os.environ.get("NLI_THREADS", os.cpu_count() or 4)))  # latenza: tutti i core (4 -> 8 sul box: -30%)
    return AutoTokenizer.from_pretrained(MODEL), AutoModelForSequenceClassification.from_pretrained(MODEL).eval()


def entailment(premises: list[str], hypothesis: str) -> tuple[float, float]:
    """Restituisce (max P(implicazione), max P(contraddizione)) sulle premesse date."""
    import torch
    tok, mod = _load()
    # latenza: le premesse corte (frasi) e quella lunga (passaggio intero) in due batch separati, così le frasi
    # non vengono riempite (padding) fino alla lunghezza del passaggio. Stesso risultato (padding mascherato), ~-45%.
    groups = sorted(range(len(premises)), key=lambda i: len(premises[i]))
    longest = len(premises[groups[-1]]) if groups else 0
    short = [i for i in groups if len(premises[i]) * 2 < longest] or []
    long_ = [i for i in groups if i not in short]
    e = c = 0.0
    for idx in (short, long_):
        if not idx:
            continue
        x = tok([premises[i] for i in idx], [hypothesis] * len(idx), return_tensors="pt", truncation=True,
                padding=True, max_length=384)
        with torch.no_grad():
            p = mod(**x).logits.softmax(-1)
        e, c = max(e, float(p[:, 0].max())), max(c, float(p[:, 2].max()))
    return e, c
