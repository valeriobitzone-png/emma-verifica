"""Esegue baseline (Emma-6 da sola) e pipeline migliorata sullo stesso test set.

uso: python run_eval.py [--testset testset.jsonl] [--tag ""]
"""
import argparse, json, statistics, time
from emma_demo.emma import EmmaGGUF, build_prompt
from emma_demo.pipeline import Pipeline
from emma_demo.scoring import label

ap = argparse.ArgumentParser()
ap.add_argument("--testset", default="testset.jsonl")
ap.add_argument("--tag", default="")
a = ap.parse_args()
items = [json.loads(l) for l in open(a.testset)]
emma = EmmaGGUF()
pipe = Pipeline(emma)


def summary(rows):
    n = len(rows); c = lambda k: sum(r["etichetta"] == k for r in rows)
    lat = [r["latenza_s"] for r in rows]
    return {"n": n, "accuratezza": round(c("corretta") / n, 3), "allucinazioni": round(c("allucinazione") / n, 3),
            "astensioni": round(c("astensione") / n, 3),
            "citazioni_non_pertinenti": round(c("citazione_non_pertinente") / n, 3), "latenza_media_s": round(statistics.mean(lat), 2),
            "latenza_p95_s": round(sorted(lat)[int(0.95 * (n - 1))], 2)}


base, impr = [], []
for it in items:
    t = time.time(); ans, _ = emma.generate(build_prompt(it["domanda"]), max_tokens=96)
    base.append({**it, "risposta": ans, "latenza_s": round(time.time() - t, 2), "etichetta": label(ans, it["gold"], it["domanda"])})
    res = pipe.answer(it["domanda"])
    lab = label(res["risposta"], it["gold"], it["domanda"])
    if lab == "allucinazione" and res["esito"] == "fallback_estrattivo":
        lab = "citazione_non_pertinente"  # frase vera di Wikipedia ma che non risponde: errore, non invenzione
    impr.append({**it, **res, "etichetta": lab})
    print(it["id"], base[-1]["etichetta"][:5], "->", impr[-1]["etichetta"][:5], res["esito"], flush=True)

for name, rows in [("baseline", base), ("migliorata", impr)]:
    with open(f"{name}{a.tag}.jsonl", "w") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
report = {"baseline": summary(base), "migliorata": summary(impr), "per_categoria": {}}
for cat in dict.fromkeys(i["categoria"] for i in items):
    report["per_categoria"][cat] = {k: summary([r for r in rows if r["categoria"] == cat])["accuratezza"]
                                    for k, rows in [("baseline", base), ("migliorata", impr)]}
esiti = [r["esito"] for r in impr]
report["esiti_pipeline"] = {e: esiti.count(e) for e in dict.fromkeys(esiti)}
json.dump(report, open(f"report{a.tag}.json", "w"), ensure_ascii=False, indent=2)
print(json.dumps(report, ensure_ascii=False, indent=2))
