"""Pipeline migliorata, senza riaddestramento:

  domanda ─► router ─► (a) strumento deterministico ─► Emma verbalizza ─► controllo del numero ─► risposta
               │
               └────► (b) Wikipedia IT ─► Emma risponde SOLO dal passaggio ─► (c) verifica NLI
                         ▲                                          │ non implicata
                         └── 2° recupero con le parole della bozza ◄┘ ─► ancora no ─► risposta estrattiva citata
                                                                                       (o astensione se nulla di pertinente)
Emma-6 resta sempre il generatore. Il verificatore (NLI) non genera testo: dice solo sì/no.
"""
from __future__ import annotations
import re, time
from .emma import build_prompt
from .retrieval import best_passage, tokens, norm, set_deadline, NET_LOG
from .tools import route
from . import nli

ENTAIL_T = 0.5


NUMW = {"zero": "0", "uno": "1", "una": "1", "due": "2", "tre": "3", "quattro": "4", "cinque": "5", "sei": "6",
        "sette": "7", "otto": "8", "nove": "9", "dieci": "10", "dodici": "12", "venti": "20", "cento": "100"}


def _numbers(t: str) -> set[str]:
    t = re.sub(r"(?<=\d)[.\s](?=\d{3}\b)", "", t)
    words = {NUMW[w] for w in re.findall(r"[a-z]+", norm(t)) if w in NUMW and w not in ("una", "uno", "sei")}
    return set(re.findall(r"\d+", t)) | words


WH = ("di che", "di quale", "qual", "quale", "chi", "che", "quanti", "quante", "quanto", "in che", "in quale", "dove", "quando", "come", "a quale")


def is_polar(q: str) -> bool:
    """Domanda sì/no (es. "I cani possono volare?")."""
    n = norm(q)
    return not n.startswith(WH) and " o " not in n


def first_sentence(text: str, question: str) -> str:
    """Tiene solo la prima frase utile: Emma tende ad aggiungere code inventate o a ripetere la domanda."""
    t = text.strip()
    t = re.split(r"(?i)\b(?:utente|emma)\s*:", t)[-1]  # Emma a volte simula un dialogo: tiene l'ultima battuta
    t = t.strip().strip('"«»\'“” ')
    for s in re.split(r"(?<=[.!?])\s+|\n|(?<=[\"»”])\s*(?=[A-Z])", t):
        s = s.strip().strip('"«»\'“” -—')
        if not s:
            continue
        if norm(question).rstrip("?. ") in norm(s):  # eco della domanda
            continue
        if s.endswith("?"):
            continue
        return s
    return ""


def hypothesis(ans: str, q: str) -> str:
    # risposte telegrafiche ("Palermo.") -> frase completa per l'NLI
    return ans if len(tokens(ans)) >= 3 else f"{q.rstrip('?')}: {ans}"


def check(ans: str, q: str, ret: dict) -> tuple[bool, float, float]:
    """(c) verifica: la frase deve (1) rispondere davvero e (2) essere implicata dal passaggio (NLI)."""
    if not ans or not ret["sentences"]:
        return False, 0.0, 0.0
    if any(x in norm(ans) for x in ("non ho", "non lo so", "non so", "contesto")):
        return False, 0.0, 0.0
    if len(tokens(ans)) > 20 or len(ans) > 160 or "AFI" in ans:
        return False, 0.0, 0.0  # frase lunga copiata dal passaggio: non è una risposta alla domanda  # rifiuto o meta-risposta: gestito dal fallback
    if is_polar(q):
        hyp = re.sub(r"^(sì|si|no)[,.!]?\s*", "", ans.strip(), flags=re.I) or ans
        if re.match(r"(?i)no\b", ans.strip()) and " non " not in f" {hyp.lower()} ":
            hyp = "Non è vero che " + hyp[0].lower() + hyp[1:]
    else:
        if not set(tokens(ans)) - set(tokens(q)):
            return False, 0.0, 0.0  # nessuna informazione nuova: Emma ha solo riformulato la domanda
        hyp = hypothesis(ans, q)
        # i numeri della risposta devono comparire nel passaggio (l'NLI da solo sbaglia spesso sui numeri)
        if not _numbers(ans) - _numbers(q) <= _numbers(ret["passage"]):
            return False, 0.0, 0.0
    e, c = nli.entailment(ret["sentences"] + [ret["passage"]], hyp)
    return e >= ENTAIL_T and c < 0.5, e, c


def shortest_supported(ans: str, q: str, ret: dict) -> str:
    """Taglia le code: restituisce la prima proposizione (prima della virgola) se da sola è già verificata."""
    head = re.split(r",\s+|\s+\(|;\s+", ans)[0].strip()
    if head != ans and check(head, q, ret)[0]:
        return head + "."
    return ans


NUMQ = ("quanti", "quante", "quanto", "in che anno", "in quale anno", "quando")
OFFTOPIC = re.compile(r"\b(e|fu) (un|una) (film|miniserie|serie televisiva|album|singolo|brano|romanzo|videogioco|marchio)\b")


def supports(question: str, s: str) -> bool:
    """Controllo di pertinenza più severo per la citazione: se fallisce si preferisce astenersi."""
    q = set(tokens(question)); st = set(tokens(s))
    if not q or len(q & st) < 2 or len(q & st) / len(q) < 0.6:
        return False
    if norm(question).startswith(NUMQ) and not (_numbers(s) - _numbers(question)):
        return False  # domanda numerica: la frase deve contenere un numero nuovo
    if OFFTOPIC.search(norm(s)) and not OFFTOPIC.search(norm(question)):
        return False  # omonimo (film, serie, marchio...) e non l'argomento chiesto
    return True


def extractive(question: str, sentences: list[str]) -> tuple[str, bool]:
    q = set(tokens(question))
    for s in sorted(sentences, key=lambda s: -len(q & set(tokens(s)))):
        if supports(question, s):
            return f"Secondo Wikipedia: «{s}»", True
    return "Non ho trovato una fonte affidabile per rispondere.", False


def statement(q: str) -> str:
    """Domanda sì/no -> affermazione da verificare ("Il ghiaccio è acqua?" -> "Il ghiaccio è acqua.")."""
    return q.strip().rstrip("?").strip() + "."


_BOUND = re.compile(r"[.!?](?=\s)|\n")


def sentence_done(question: str):
    """Criterio di arresto anticipato: c'è già una frase completa (seguita da spazio/a capo) che first_sentence
    accetterebbe. Il resto del testo verrebbe comunque scartato da first_sentence."""
    def done(text: str) -> bool:
        ends = [m.end() for m in _BOUND.finditer(text)]
        return bool(ends) and bool(first_sentence(text[:ends[-1]], question))
    return done


class Pipeline:
    def __init__(self, emma, early_stop: bool = True):
        self.emma = emma
        self.early_stop = early_stop

    def _ask(self, q: str, passage: str) -> str:
        prompt = (f"Contesto: {passage}\n"
                  + build_prompt(f"Rispondi in una frase breve usando solo le informazioni del contesto. {q}")[1:])
        return self._gen(prompt, 64, q)

    def _gen(self, prompt: str, max_tokens: int, q: str) -> str:
        if self.early_stop and hasattr(self.emma, "generate_until"):
            return self.emma.generate_until(prompt, sentence_done(q), max_tokens=max_tokens)[0]
        return self.emma.generate(prompt, max_tokens=max_tokens)[0]

    def answer(self, q: str) -> dict:
        t0 = time.time()
        r = route(q)
        if r:  # ---- (a) strumenti deterministici; Emma verbalizza il risultato
            prompt = (f"Contesto: risultato verificato da uno strumento di calcolo: {r['risultato']}.\n"
                      + build_prompt(f"{q} Rispondi con una frase breve usando esattamente il risultato del contesto.")[1:])
            raw = self._gen(prompt, 48, q)
            gen = first_sentence(raw, q)
            ok = bool(re.search(r"(?<![\w,.])" + re.escape(norm(r["risultato"])) + r"(?![\w]|[.,]\d)", norm(gen))) and _numbers(gen) <= _numbers(r["risultato"]) | _numbers(q)
            return {"percorso": "strumento:" + r["tool"], "risultato_strumento": r["risultato"], "emma_grezza": raw,
                    "risposta": gen if ok else f"La risposta è {r['risultato']}.",
                    "esito": "emma_verificata" if ok else "fallback_strumento", "latenza_s": round(time.time() - t0, 2)}
        # ---- (b) recupero + generazione ancorata (tetto di 30 s alla rete per domanda)
        NET_LOG.clear(); set_deadline(30)
        try:
            ret = best_passage(q, n_sent=4)
        except Exception as e:
            ret = {"passage": "", "titles": [], "sentences": [], "errore": str(e)}
        if not ret["passage"]:
            return {"percorso": "wiki", "risposta": "Non ho trovato una fonte affidabile per rispondere.",
                    "esito": "nessuna_fonte", "rete": list(NET_LOG), "latenza_s": round(time.time() - t0, 2)}
        if is_polar(q):
            # verifica frase per frase: conta solo una frase che parla davvero del predicato chiesto
            st = statement(q); need = set(tokens(st))
            e = c = 0.0; yes_s = no_s = None
            for x in ret["sentences"]:
                if not need or len(need & set(tokens(x))) / len(need) < 0.6:
                    continue
                ex, cx = nli.entailment([x], st)
                e, c = max(e, ex), max(c, cx)
                if ex >= 0.7 and cx < 0.3 and yes_s is None: yes_s = x
                if cx >= 0.7 and ex < 0.3 and no_s is None: no_s = x
            if bool(yes_s) != bool(no_s):
                final, esito = f"{'Sì' if yes_s else 'No'}. Secondo Wikipedia: «{yes_s or no_s}»", "sinon_verificato"
            else:
                final, esito = "Non ho trovato una fonte che confermi o smentisca con sicurezza.", "astensione"
            return {"percorso": "wiki:sì/no", "fonti": ret["titles"], "passaggio": ret["passage"],
                    "p_implicazione": round(e, 3), "p_contraddizione": round(c, 3), "risposta": final,
                    "esito": esito, "latenza_s": round(time.time() - t0, 2), "rete": list(NET_LOG)}
        raw = self._ask(q, ret["passage"]); ans = first_sentence(raw, q)
        ok, e, c = check(ans, q, ret)
        giro = 1
        if not ok and ans:  # (c) 2° recupero guidato dalla bozza di Emma, poi nuova verifica
            try:
                ret2 = best_passage(q + " " + " ".join(tokens(ans)[:4]), n_sent=4)
            except Exception:
                ret2 = {"passage": ""}
            if ret2["passage"] and ret2["passage"] != ret["passage"]:
                ok2, e2, c2 = check(ans, q, ret2)
                giro = 2
                if ok2 or e2 > e:
                    ret, ok, e, c = ret2, ok2, e2, c2
        if ok:
            final, esito = shortest_supported(ans, q, ret), "emma_verificata"
        else:
            final, found = extractive(q, ret["sentences"])
            esito = "fallback_estrattivo" if found else "astensione"
        return {"percorso": "wiki", "fonti": ret["titles"], "passaggio": ret["passage"], "emma_grezza": raw,
                "emma_prima_frase": ans, "p_implicazione": round(e, 3), "p_contraddizione": round(c, 3),
                "giri_recupero": giro, "risposta": final, "esito": esito, "latenza_s": round(time.time() - t0, 2),
                "rete": list(NET_LOG)}
