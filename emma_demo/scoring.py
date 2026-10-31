"""Valutazione automatica: corretta / astensione / allucinazione.

Regola anti-eco: un numero gold che compare già nella domanda conta solo se nella risposta
compare più volte che nella domanda (es. "144 diviso 12 = 144" NON è corretta).
"""
import re
from .retrieval import norm

ABST = ["non lo so", "non so ", "non sono in grado", "non posso", "non trovo", "non ho trovato", "il contesto non",
        "non e indicat", "non e possibile", "non ho informazioni", "non dispongo"]


OPER = r"\d+(?:[.,]\d+)?\s*(?:×|x|\*|diviso(?: per)?|per|\+|più|-|meno|:|/|elevato alla)\s*\d+(?:[.,]\d+)?"


def _clean(answer: str, question: str) -> str:
    """Toglie l'eco della domanda e le espressioni con gli operandi (es. "144 diviso 12"),
    così un numero copiato dalla domanda non viene scambiato per la risposta."""
    a, q = norm(answer), norm(question).rstrip("?. ")
    if q:
        a = a.replace(q, " ")
    return re.sub(OPER, " ", a)


def is_correct(answer: str, gold: list[str], question: str = "") -> bool:
    a = _clean(answer, question)
    for g in map(norm, gold):
        if g in ("no", "si"):
            if re.match(r"\W*" + g + r"\b", a) or re.search(r"risposta e " + g + r"\b", a):
                return True
            continue
        if re.search(r"(?<![\w.,])" + re.escape(g) + r"(?![\w]|[.,]\d)", a):
            return True
    return False


def label(answer: str, gold: list[str], question: str = "") -> str:
    if is_correct(answer, gold, question):
        return "corretta"
    a = norm(answer)
    if not a.strip() or any(x in a for x in ABST):
        return "astensione"
    return "allucinazione"
