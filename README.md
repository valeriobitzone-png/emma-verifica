# Emma-6 + verifica: meno risposte inventate, misurate

Un piccolo esperimento aperto: prendere [Emma-6](https://huggingface.co/egomnia/emma-6), il modello linguistico italiano di Egomnia S.p.A., e metterci intorno uno strato esterno di **grounding, verifica e astensione**, senza riaddestrarlo e senza toccarne i pesi. L'obiettivo è misurare quante risposte inventate si riescono a fermare prima che arrivino all'utente.

È un contributo, non una critica. Emma-6 è un modello piccolo (1,55 miliardi di parametri), addestrato da zero in italiano, e la stessa model card indica allucinazioni e inesattezze tra i limiti noti. Per un modello di queste dimensioni, dire "non lo so" o appoggiarsi a una fonte è più realistico che sapere tutto. Questo repo prova a misurarlo.

**Demo online (risultati reali di heldout3, a confronto):** https://huggingface.co/spaces/Ambrogio26/emma-verifica-demo

## Come funziona

Emma-6 resta sempre il generatore. Intorno ci sono quattro passaggi (`emma_demo/pipeline.py`):

1. **Router strumenti** (`tools.py`): aritmetica, date, unità di misura e conteggio delle lettere vengono calcolati in modo deterministico. Emma verbalizza il risultato e si controlla che il numero coincida; se non coincide, si usa direttamente l'output dello strumento.
2. **Grounding su Wikipedia in italiano** (`retrieval.py`): si recupera il passaggio più pertinente ed Emma risponde solo a partire da quel passaggio.
3. **Verifica di supporto** (`nli.py`): un modello NLI multilingue (`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`) controlla se il passaggio implica la risposta (soglia 0,5). Se non la implica, si fa un secondo giro di recupero.
4. **Fallback estrattivo o astensione**: se la risposta resta non supportata, si restituisce una frase di Wikipedia citata oppure ci si astiene.

`scoring.py` etichetta ogni risposta come corretta, allucinazione, astensione o citazione non pertinente (cioè una frase vera che non risponde alla domanda).

## Come eseguirlo

Requisiti: Python 3.11+, circa 4 GB di disco, connessione di rete (per Hugging Face e per l'API di Wikipedia).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./scripts/scarica_modello.sh          # scarica i pesi in ./model (non inclusi nel repo)
(cd data && sha256sum -c heldout3.sha256)
python run_eval.py --testset data/heldout3.jsonl --tag _heldout3
```

Output: `baseline<tag>.jsonl`, `migliorata<tag>.jsonl`, `report<tag>.json`. Le risposte di Wikipedia vengono salvate in `cache/wiki`.

**Pesi del modello.** Questo repo non contiene né ridistribuisce pesi. Lo script scarica:
- dal repo ufficiale `egomnia/emma-6`: tokenizer, configurazione ed export ONNX INT8 (backend `EmmaONNX`, lento perché senza KV cache);
- la conversione GGUF Q8_0 di terzi `PaoloneSborracchione/emma-6-GGUF` (non ufficiale Egomnia), usata con llama.cpp per i run misurati (backend `EmmaGGUF`). L'hash del file è verificato.

L'uso del modello è soggetto alla licenza OpenRAIL di Emma-6 e alle sue restrizioni d'uso: leggete la [model card](https://huggingface.co/egomnia/emma-6) prima di usarlo.

## Risultati

Numeri copiati dai file in `risultati/`. Il set di riferimento è **heldout3**: 60 domande nuove, codice v3b congelato.

| Sistema (heldout3, n=60) | Accuratezza | Allucinazioni | Astensioni | Citazioni non pertinenti | Latenza media | Latenza p95 |
|---|---|---|---|---|---|---|
| Emma-6 da sola | 23,3% | 75,0% | 1,7% | 0,0% | 3,40 s | 8,88 s |
| Emma-6 + verifica | 68,3% | 3,3% | 18,3% | 10,0% | 11,43 s | 30,58 s |

Fonte: `risultati/report_heldout3_run2.json`. In numeri assoluti, le risposte inventate passano da 45 su 60 a 2 su 60. Le latenze di questo run sono gonfiate dal carico della macchina (anche la baseline è più lenta del solito). Sui set precedenti la latenza media è passata da circa 0,9 s a circa 2,4 s.

Set usati durante lo sviluppo (risultati **ottimistici**, vedi `risultati.md`):

| Set | n | Accuratezza base → verifica | Allucinazioni base → verifica |
|---|---|---|---|
| testset | 83 | 27,7% → 85,5% | 71,1% → 2,4% |
| heldout | 24 | 20,8% → 83,3% | 75,0% → 4,2% |
| heldout2 | 22 | 18,2% → 81,8% | 77,3% → 0,0% |

## Limiti, detti onestamente

- Le allucinazioni sono **ridotte, non eliminate**.
- Una parte del miglioramento viene da astensioni (18,3%) e da citazioni vere ma non pertinenti (10%): sono meno dannose di un'invenzione, ma restano risposte non utili.
- Non è il modello a diventare più bravo. Gran parte del guadagno viene dagli strumenti deterministici e da Wikipedia; nelle categorie geografia e senso comune, su heldout3, la pipeline va peggio della baseline (vedi `per_categoria` nel report).
- Il codice è stato iterato (v1 → v3dev → v3 → v3b) guardando testset, heldout e heldout2. Solo heldout3 è stato misurato con il codice congelato, e anche heldout3 era già stato visto una volta da v3 prima del congelamento.
- L'etichettatura è automatica (match di stringhe), senza revisione umana. I set sono piccoli e non ci sono intervalli di confidenza.
- La latenza è più alta e il sistema dipende dalla rete per Wikipedia.
- Le domande sono semplici e fattuali; il comportamento su testi lunghi, conversazioni o domini aziendali non è stato misurato.
- Unica modifica rispetto al codice congelato: lo User-Agent verso Wikipedia in `retrieval.py` (nessun effetto sulla logica).

## Struttura

```
emma_demo/   pipeline, strumenti, recupero, NLI, scoring, wrapper Emma-6
run_eval.py  baseline vs pipeline sullo stesso set
data/        set di domande (con hash di heldout3)
scripts/     generatori dei set e download del modello
risultati/   report e risposte del run di riferimento
```

## Crediti e licenze

- Emma-6: Egomnia S.p.A., licenza OpenRAIL. Model card: https://huggingface.co/egomnia/emma-6
- Modello NLI: MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (vedi la sua model card).
- Testi da Wikipedia in italiano (CC BY-SA), recuperati tramite API pubblica.
- Il codice di questo repo è rilasciato con licenza Apache-2.0 (vedi `LICENSE`) e non include pesi di modelli.

Valerio Falzone
