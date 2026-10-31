"""Profilazione per stadio della pipeline (tempi reali). uso: python scripts/profile_stages.py [--n 8] [--gguf path] [--threads N]"""
import argparse, json, os, sys, time, collections
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser(); ap.add_argument("--ids", default="n1,n8,g1,g5,s1,s5,c1,c5,f1,f5")
ap.add_argument("--gguf", default=None); ap.add_argument("--threads", type=int, default=None); ap.add_argument("--passes", type=int, default=2)
a = ap.parse_args()
T = collections.defaultdict(float)
def wrap(mod, name, key):
    f = getattr(mod, name)
    def g(*x, **k):
        t = time.time()
        try: return f(*x, **k)
        finally: T[key] += time.time() - t
    setattr(mod, name, g)
t = time.time()
from emma_demo import emma as E, nli, retrieval as R, pipeline as P
import emma_demo.tools as TL
T0 = {"import_s": time.time() - t}
t = time.time(); em = E.EmmaGGUF(path=a.gguf, n_threads=a.threads); T0["load_emma_s"] = time.time() - t
t = time.time(); nli._load(); T0["load_nli_s"] = time.time() - t
print(json.dumps({k: round(v, 2) for k, v in T0.items()}))
wrap(R, "_get", "rete_wiki"); wrap(P, "best_passage", "retrieval_tot"); wrap(nli, "entailment", "nli"); wrap(P, "route", "router")
_g = em.generate
def gen(*x, **k):
    t = time.time(); r = _g(*x, **k); T["emma_gen"] += time.time() - t; T["emma_calls"] += 1; return r
em.generate = gen
pipe = P.Pipeline(em)
items = {json.loads(l)["id"]: json.loads(l) for l in open("data/heldout3.jsonl")}
rows = []
for ps in range(a.passes):
    for i in a.ids.split(","):
        T.clear(); t = time.time(); r = pipe.answer(items[i]["domanda"]); tot = time.time() - t
        row = {"pass": ps, "id": i, "tot": round(tot, 2), **{k: round(v, 2) for k, v in T.items()}, "esito": r["esito"]}
        row["retrieval_cpu"] = round(row.get("retrieval_tot", 0) - row.get("rete_wiki", 0), 2)
        rows.append(row); print(json.dumps(row), flush=True)
for ps in range(a.passes):
    rr = [r for r in rows if r["pass"] == ps]
    keys = ["tot", "router", "retrieval_tot", "rete_wiki", "emma_gen", "emma_calls", "nli"]
    print("PASS", ps, json.dumps({k: round(sum(r.get(k, 0) for r in rr) / len(rr), 3) for k in keys}))
