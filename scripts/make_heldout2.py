"""Secondo set di controllo, scritto DOPO le correzioni v2 e PRIMA di eseguirle: mai visto in sviluppo."""
import json
Q = [
 ("aritmetica","Fammi il conto: 17 per 3",["51"]),
 ("aritmetica","Quanto viene 90 diviso 4?",["22,5","22.5"]),
 ("aritmetica","Quanto fa 7 al quadrato?",["49"]),
 ("aritmetica","Se ho 35 euro e ne spendo 12, quanti me ne restano?",["23"]),
 ("date","In che giorno della settimana cade il 1 gennaio 2027?",["venerdì","venerdi"]),
 ("date","Quanti giorni ha aprile?",["30","trenta"]),
 ("date","Quanti anni ha una persona nata nel 1990 nel 2026?",["36"]),
 ("unita","Quanti metri sono 2,5 chilometri?",["2500","2.500"]),
 ("unita","Quante ore ci sono in 2 giorni?",["48"]),
 ("lettere","Quante l ci sono nella parola collana?",["2","due"]),
 ("geografia","Qual è la capitale dell'Irlanda?",["dublino"]),
 ("geografia","Qual è la capitale della Svezia?",["stoccolma"]),
 ("geografia","Qual è il capoluogo del Piemonte?",["torino"]),
 ("geografia","In quale regione si trova Perugia?",["umbria"]),
 ("storia","In che anno è stato eletto papa Francesco?",["2013"]),
 ("storia","Chi ha scoperto la penicillina?",["fleming"]),
 ("cultura","Chi ha scritto Il Principe?",["machiavelli"]),
 ("cultura","Chi ha composto Il barbiere di Siviglia?",["rossini"]),
 ("scienza","Qual è il simbolo chimico dell'argento?",["ag"]),
 ("scienza","Quanti cromosomi ha una cellula umana?",["46"]),
 ("senso_comune","Un gatto ha le piume?",["no"]),
 ("senso_comune","Il ghiaccio è acqua allo stato solido?",["sì","si"]),
]
with open("heldout2.jsonl","w") as f:
    for i,(c,q,a) in enumerate(Q,1):
        f.write(json.dumps({"id":f"k{i}","categoria":c,"domanda":q,"gold":a,"nota":"held-out 2"},ensure_ascii=False)+"\n")
print(len(Q))
