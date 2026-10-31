"""Set di controllo (held-out): domande formulate diversamente, scritte PRIMA di rieseguire la pipeline
e mai usate per mettere a punto router/recupero. Serve a misurare l'overfitting."""
import json
Q = [
 ("aritmetica","Mi calcoli 13 per 7?",["91"]),
 ("aritmetica","Quanto fa 48 diviso 6?",["8"]),
 ("aritmetica","Quanto fa 250 più 175?",["425"]),
 ("aritmetica","Quanto è il 15% di 80?",["12"]),
 ("aritmetica","Moltiplica 11 per 11",["121"]),
 ("date","Che giorno della settimana era il 2 giugno 1946?",["domenica"]),
 ("date","Il 2028 sarà bisestile?",["sì","si"]),
 ("date","Quanti giorni mancano dal 1 novembre 2026 al 25 dicembre 2026?",["54"]),
 ("unita","Quanti grammi ci sono in 3 etti?",["300"]),
 ("unita","Quanti centimetri ci sono in 2 metri?",["200"]),
 ("lettere","Quante e ci sono nella parola elefante?",["3","tre"]),
 ("lettere","Quante o ci sono nella parola ottobre?",["2","due"]),
 ("geografia","Qual è la capitale del Portogallo?",["lisbona"]),
 ("geografia","Qual è la capitale della Grecia?",["atene"]),
 ("geografia","Qual è il capoluogo della Toscana?",["firenze"]),
 ("geografia","In quale regione si trova Bari?",["puglia"]),
 ("storia","In che anno è morto Giulio Cesare?",["44"]),
 ("storia","In che anno è stato firmato il Trattato di Roma che istituì la CEE?",["1957"]),
 ("cultura","Chi ha scritto il Decameron?",["boccaccio"]),
 ("cultura","Chi ha dipinto L'ultima cena di Milano?",["leonardo"]),
 ("scienza","Qual è il simbolo chimico del ferro?",["fe"]),
 ("scienza","Qual è il pianeta rosso?",["marte"]),
 ("senso_comune","Un pinguino sa volare?",["no"]),
 ("senso_comune","Quante ore ha un giorno?",["24","ventiquattro"]),
]
with open("heldout.jsonl","w") as f:
    for i,(c,q,a) in enumerate(Q,1):
        f.write(json.dumps({"id":f"h{i}","categoria":c,"domanda":q,"gold":a,"nota":"held-out"},ensure_ascii=False)+"\n")
print(len(Q))
