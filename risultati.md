# Risultati (numeri copiati dai file report*.json)

Accur. = accuratezza, Alluc. = tasso di allucinazione, Ast. = astensioni, Cit.NP = citazioni non pertinenti (unica misura legata alle citazioni; la correttezza delle citazioni non è misurata direttamente), latenza media / p95 in secondi.

| Set (report) | Codice | n | Sistema | Accur. | Alluc. | Ast. | Cit.NP | Lat. media | Lat. p95 |
|---|---|---|---|---|---|---|---|---|---|
| testset (risultati/report_v3_testset.json) | v3 | 83 | baseline | 0.277 | 0.711 | 0.012 | 0.000 | 0.88 | 1.77 |
| | | | migliorata | 0.855 | 0.024 | 0.072 | 0.048 | 2.51 | 5.82 |
| heldout (risultati/report_v3_heldout.json) | v3 | 24 | baseline | 0.208 | 0.750 | 0.042 | 0.000 | 0.84 | 1.28 |
| | | | migliorata | 0.833 | 0.042 | 0.125 | 0.000 | 2.40 | 5.50 |
| heldout2 (risultati/report_v3_heldout2.json) | v3 | 22 | baseline | 0.182 | 0.773 | 0.045 | 0.000 | 0.94 | 1.84 |
| | | | migliorata | 0.818 | 0.000 | 0.136 | 0.045 | 2.23 | 6.09 |
| **heldout3 (risultati/report_heldout3_run2.json)** | **v3b congelato** | 60 | baseline | 0.233 | 0.750 | 0.017 | 0.000 | 3.40 | 8.88 |
| | | | migliorata | 0.683 | 0.033 | 0.183 | 0.100 | 11.43 | 30.58 |

Esiti pipeline heldout3 run2: fallback_strumento 20, fallback_estrattivo 17, emma_verificata 11, astensione 9, nessuna_fonte 2, sinon_verificato 1.

## Note
- testset/heldout/heldout2 sono stati usati durante lo sviluppo (v1→v3dev→v3): risultati ottimistici. heldout3 con v3b congelato è la stima più onesta.
- Il primo run di heldout3 (risultati/report_heldout3.json, codice precedente a v3b, 15:05) dava migliorata 0.450 acc., 0.017 alluc., 0.483 astensioni (25 `nessuna_fonte`). Il run2 è quello di riferimento.
- Latenze del run2 (anche baseline 3.40 s contro ~0.8 s nel run1) probabilmente gonfiate da carico concorrente della CPU/rete: non confrontabili con gli altri set.
- Storico: risultati storici (non inclusi) (v1) migliorata 0.542 acc. / 0.333 alluc.; report.json, report_heldout*.json, report_v3dev_*.json sono versioni intermedie.

## Latenza (run del 31/10, codice prima/dopo il branch latency)

Ottimizzazioni (branch `latency`): Emma genera in streaming e si ferma alla prima frase utile; l'NLI elabora frasi e passaggio in batch separati (niente padding inutile) con tutti i core; una chiamata all'API di Wikipedia in meno (i redirect erano già nella risposta).
Misure reali sul box di sviluppo (CPU 8 core), heldout3, n=60, stessa cache Wikipedia congelata per prima e dopo:

| Pipeline | Accur. | Alluc. | Lat. media | Lat. p95 |
|---|---|---|---|---|
| prima | 0,717 | 0,033 | 2,16 s | 5,32 s |
| dopo | 0,717 | 0,033 | 1,48 s | 3,61 s |

Accuratezza e allucinazioni invariate (cambia una sola risposta, n36, sempre corretta). Report: `risultati/latency/`.

