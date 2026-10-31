"""Router + strumenti deterministici (aritmetica, date, unità, conteggio lettere).

route(domanda) -> dict(tool=..., risultato=str) oppure None se nessuno strumento si applica.
"""
from __future__ import annotations
import ast, calendar, datetime as dt, math, operator, re

GIORNI = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
MESI = {m: i for i, m in enumerate(["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
                                    "agosto", "settembre", "ottobre", "novembre", "dicembre"], 1)}
NUM = r"(\d+(?:[.,]\d+)?)"


def _n(s: str) -> float:
    return float(s.replace(",", "."))


def _fmt(x: float) -> str:
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else f"{x:g}".replace(".", ",")


# ---------- aritmetica sicura (AST, niente eval) ----------
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg}


def _safe_eval(expr: str) -> float:
    def ev(n):
        if isinstance(n, ast.Expression): return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)): return n.value
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS: return _OPS[type(n.op)](ev(n.operand))
        raise ValueError("espressione non ammessa")
    return ev(ast.parse(expr, mode="eval"))


def arithmetic(q: str):
    s = q.lower()
    if m := re.search(r"(?:ho|avevo) " + NUM + r"\b.*?\b(?:ne )?(?:spendo|perdo|regalo|tolgo) " + NUM, s):
        return _fmt(_n(m[1]) - _n(m[2]))
    if m := re.search(r"radice quadrata di " + NUM, s):
        return _fmt(math.sqrt(_n(m[1])))
    if m := re.search(NUM + r"\s*(?:%|per cento) di " + NUM, s):
        return _fmt(_n(m[1]) * _n(m[2]) / 100)
    if m := re.search(NUM + r" al (quadrato|cubo)\b", s):
        return _fmt(_n(m[1]) ** (2 if m[2] == "quadrato" else 3))
    if m := re.search(NUM + r" elevato (?:alla|a) " + NUM, s):
        return _fmt(_n(m[1]) ** _n(m[2]))
    # espressione aritmetica ovunque nella frase (numeri legati da operatori o parole-operatore)
    OPW = r"(?:\s*(?:moltiplicato per|diviso per|diviso|per|x|×|\*|più|\+|meno|-|:|/|\^)\s*)"
    m = re.search(r"\(?\d+(?:[.,]\d+)?\)?(?:" + OPW + r"\(?\d+(?:[.,]\d+)?\)?)+", s)
    if not m:
        return None
    e = m[0]
    for a, b in [("moltiplicato per", "*"), ("diviso per", "/"), ("diviso", "/"), ("per", "*"), ("x", "*"),
                 ("×", "*"), ("più", "+"), ("meno", "-"), (":", "/"), ("^", "**")]:
        e = e.replace(a, f" {b} ")
    e = e.replace(",", ".")
    if not re.fullmatch(r"[\d\s.+\-*/()]+", e):
        return None
    try:
        return _fmt(_safe_eval(e))
    except Exception:
        return None


# ---------- date ----------
def _date(s: str):
    m = re.search(r"(\d{1,2})(?:°)? (" + "|".join(MESI) + r") (\d{4})", s)
    return (dt.date(int(m[3]), MESI[m[2]], int(m[1])), m.end()) if m else (None, 0)


def dates(q: str):
    s = q.lower()
    if "giorno della settimana" in s or "che giorno" in s:
        d, _ = _date(s)
        if d: return GIORNI[d.weekday()]
    if m := re.search(r"(\d{4}) (?:è|sarà|era|fu|è stato|sarà un) ?(?:un anno )?bisestile", s):
        return "sì" if calendar.isleap(int(m[1])) else "no"
    if m := re.search(r"quanti giorni ha (\w+) nel (\d{4})", s):
        if m[1] in MESI: return str(calendar.monthrange(int(m[2]), MESI[m[1]])[1])
    if m := re.search(r"quanti giorni ha (\w+)\??$", s.strip()):
        if m[1] in MESI:
            return "28 (29 negli anni bisestili)" if m[1] == "febbraio" else str(calendar.monthrange(2026, MESI[m[1]])[1])
    if m := re.search(r"nat[oa] nel (\d{4}),? (?:quanti anni ha )?nel (\d{4})", s):
        return str(int(m[2]) - int(m[1]))  # età al compimento del compleanno
    if "quanti giorni ha un anno bisestile" in s:
        return "366"
    if "giorni" in s:
        d1, end = _date(s); d2, _ = _date(s[end:])
        if d1 and d2: return str(abs((d2 - d1).days))
    if m := re.search(r"quanti anni (?:sono passati |ci sono )?dal (\d{3,4}) al (\d{3,4})", s):
        return str(int(m[2]) - int(m[1]))
    return None


# ---------- unità ----------
UNITA = {  # nome -> (grandezza, fattore verso unità base)
    "chilometri": ("l", 1000), "chilometro": ("l", 1000), "km": ("l", 1000), "metri": ("l", 1), "metro": ("l", 1),
    "centimetri": ("l", .01), "millimetri": ("l", .001),
    "chilogrammi": ("m", 1000), "chilogrammo": ("m", 1000), "chili": ("m", 1000), "chilo": ("m", 1000),
    "kg": ("m", 1000), "grammi": ("m", 1), "grammo": ("m", 1), "etti": ("m", 100),
    "ore": ("t", 3600), "ora": ("t", 3600), "un'ora": ("t", 3600), "minuti": ("t", 60), "minuto": ("t", 60),
    "secondi": ("t", 1), "giorni": ("t", 86400), "giorno": ("t", 86400),
    "litri": ("v", 1), "litro": ("v", 1), "millilitri": ("v", .001), "centilitri": ("v", .01),
}
_U = "|".join(sorted(map(re.escape, UNITA), key=len, reverse=True))


def units(q: str):
    s = q.lower().replace("un'ora", "1 ora").replace("un chilo", "1 chilo")
    if m := re.search(r"quant[ie] (" + _U + r") (?:ci )?(?:sono|ha|ha?nno)? ?(?:in |sono )?" + NUM + r" (" + _U + r")", s):
        to, val, frm = m[1], _n(m[2]), m[3]
        if UNITA[to][0] == UNITA[frm][0]:
            return _fmt(val * UNITA[frm][1] / UNITA[to][1])
    # "pesa di più un chilo di X o un chilo di Y?" -> stessa quantità
    if m := re.search(r"pesa (?:di )?più (?:un|1) (\w+) di \w+ o (?:un|1) (\w+) di \w+", s):
        if m[1] in UNITA and m[2] in UNITA and UNITA[m[1]] == UNITA[m[2]]:
            return "pesano uguale"
    return None


def letters(q: str):
    s = q.lower()
    if m := re.search(r"quante ([a-zàèéìòù]) ci sono nella parola ([\wàèéìòù]+)", s):
        return str(m[2].count(m[1]))
    if m := re.search(r"quante lettere ha la parola ([\wàèéìòù]+)", s):
        return str(len(m[1]))
    return None


TOOLS = [("lettere", letters), ("date", dates), ("unita", units), ("aritmetica", arithmetic)]


def route(q: str):
    for name, fn in TOOLS:
        try:
            r = fn(q)
        except Exception:
            r = None
        if r is not None:
            return {"tool": name, "risultato": r}
    return None
