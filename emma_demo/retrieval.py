"""Recupero di passaggi da Wikipedia in italiano (API pubblica, con cache su disco)."""
from __future__ import annotations
import json, hashlib, re
from pathlib import Path
import requests

API = "https://it.wikipedia.org/w/api.php"
UA = {"User-Agent": "emma-grounding-demo/0.1 (ricerca; https://github.com/valeriobitzone-png/emma-verifica)"}
CACHE = Path(__file__).resolve().parent.parent / "cache" / "wiki"
STOP = set("il lo la i gli le un uno una di a da in con su per tra fra e o che chi è qual quale quali quanto quanti "
           "quante come dove quando cosa del della dei degli delle al alla ai agli alle dal dalla nel nella sul sulla "
           "ha sono era stato stata anno anni si non più ci ne d l".split())


def norm(t: str) -> str:
    """Minuscolo senza diacritici (Tōkyō -> tokyo, è -> e)."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(c))


def tokens(t: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", norm(t)) if w not in STOP and len(w) > 1]


SESSION = requests.Session()
DEADLINE = [None]  # scadenza globale (time.time()) per la domanda corrente, impostata dalla pipeline
NET_LOG: list = []
LAST = [0.0]
MIN_GAP = 0.5  # (secondi, esito) per ogni chiamata di rete: serve a diagnosticare la latenza


def set_deadline(seconds: float | None):
    import time
    DEADLINE[0] = None if seconds is None else time.time() + seconds


def _get(params: dict) -> dict:
    """GET con cache. CAUSA DEL VECCHIO OUTLIER (386 s): 5 tentativi x timeout 20 s + attese, ripetuti su
    3-6 chiamate per domanda, senza alcun tetto complessivo. Ora: timeout breve, 2 tentativi, scadenza globale."""
    import time
    CACHE.mkdir(parents=True, exist_ok=True)
    key = CACHE / (hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest() + ".json")
    if key.exists():
        return json.loads(key.read_text())
    for attempt in range(4):
        left = 8.0 if DEADLINE[0] is None else DEADLINE[0] - time.time()
        if left <= 0.5:
            break
        gap = time.time() - LAST[0]
        if gap < MIN_GAP:  # max ~2 richieste/s: l'API pubblica risponde 429 se si va più veloci
            time.sleep(MIN_GAP - gap)
        t = time.time(); LAST[0] = t; r = None
        try:
            r = SESSION.get(API, params={**params, "format": "json", "formatversion": 2}, headers=UA,
                            timeout=(3, min(6.0, left)))
            js = r.json() if r.ok else None
        except Exception as e:
            NET_LOG.append((round(time.time() - t, 2), type(e).__name__)); js = None
        else:
            NET_LOG.append((round(time.time() - t, 2), r.status_code))
        if js is not None and "error" not in js:
            key.write_text(r.text)
            return js
        wait = 2.0 ** attempt  # 1, 2, 4, 8 s (backoff esponenziale), sempre entro la scadenza globale
        if r is not None and r.headers.get("Retry-After", "").isdigit():
            wait = max(wait, float(r.headers["Retry-After"]))
        time.sleep(max(0.0, min(wait, (DEADLINE[0] or time.time() + 8) - time.time() - 0.5)))
    raise RuntimeError("API Wikipedia non disponibile (entro il tempo massimo)")


def search(query: str, k: int = 3, extra_titles: list[str] = ()) -> list[dict]:
    """Restituisce le pagine (ricerca full-text + titoli esatti) con l'introduzione in testo semplice."""
    hits = _get({"action": "query", "list": "search", "srsearch": query, "srlimit": k})["query"]["search"]
    hits = [{"title": t} for t in extra_titles] + [h for h in hits if h["title"] not in extra_titles]
    if not hits:
        return []
    titles = "|".join(h["title"] for h in hits[:20])
    pages = _get({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1, "redirects": 1,
                  "titles": titles})["query"]["pages"]
    by = {p["title"]: p.get("extract", "") for p in pages}
    # segue i redirect (es. "Pinocchio" -> titolo reale)
    q = _get({"action": "query", "redirects": 1, "titles": titles})["query"]
    for r in q.get("redirects", []):
        by.setdefault(r["from"], by.get(r["to"], ""))
    return [{"title": h["title"], "text": by.get(h["title"], "")} for h in hits if by.get(h["title"])]


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ù0-9])", text) if len(s.strip()) > 15]


def best_passage(question: str, k_pages: int = 5, n_sent: int = 3) -> dict:
    """Sceglie le n frasi con maggiore sovrapposizione lessicale con la domanda."""
    q = set(tokens(question))
    scored = []
    # titoli esatti per le parole chiave più "da voce enciclopedica" (nomi propri e ultime parole)
    words = re.findall(r"[A-Za-zÀ-ù']+", question)
    qwords = {"Qual", "Quale", "Chi", "Che", "Quanti", "Quante", "Quanto", "In", "Il", "La", "Una", "Un", "I", "Di", "A"}
    ents = [w.split("'")[-1] for w in words if w[0].isupper() and w not in qwords]
    kw = tokens(question)
    cand = list(dict.fromkeys([e.capitalize() for e in ents] + [w.capitalize() for w in kw[-2:]]))[:4]
    for rank, p in enumerate(search(" ".join(kw) or question, k_pages, cand)):
        title_bonus = len(q & set(tokens(p["title"]))) * 0.5
        for i, s in enumerate(sentences(p["text"])[:15]):
            ov = len(q & set(tokens(s)))
            scored.append((ov + title_bonus - 0.3 * rank - 0.05 * i, s, p["title"]))
    scored.sort(key=lambda x: -x[0])
    top = scored[:n_sent]
    return {"passage": " ".join(s for _, s, _ in top), "titles": sorted({t for _, _, t in top}),
            "sentences": [s for _, s, _ in top]}
