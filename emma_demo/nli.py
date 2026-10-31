"""Verifica di implicazione (NLI) multilingue: la frase di Emma è implicata dal passaggio?
Modello: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (~280M, CPU, ~50 ms a coppia)."""
from __future__ import annotations
from functools import lru_cache

MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"


@lru_cache(1)
def _load():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    torch.set_num_threads(4)
    return AutoTokenizer.from_pretrained(MODEL), AutoModelForSequenceClassification.from_pretrained(MODEL).eval()


def entailment(premises: list[str], hypothesis: str) -> tuple[float, float]:
    """Restituisce (max P(implicazione), max P(contraddizione)) sulle premesse date."""
    import torch
    tok, mod = _load()
    x = tok(premises, [hypothesis] * len(premises), return_tensors="pt", truncation=True, padding=True, max_length=384)
    with torch.no_grad():
        p = mod(**x).logits.softmax(-1)
    return float(p[:, 0].max()), float(p[:, 2].max())
