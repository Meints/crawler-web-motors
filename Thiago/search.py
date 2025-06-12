#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
search.py – busca BM25 (query única, lote ou REPL)

• query única ........... python search.py "onix 2020 automático" -k 15
• lote (arquivo) ........ python search.py -f consultas.txt -o saida.csv -k 20
• modo interativo ....... python search.py           # entra num loop
"""

import json, math, re, string, argparse, csv, sys
from collections import defaultdict
try:
    from tabulate import tabulate
    TABS = True
except ImportError:
    TABS = False

# ---------- preprocessing (igual ao index) ----------
STOP = {"de","a","o","que","e","do","da","em","um","para","é","com","não",
        "uma","os","no","se","na","por","mais","as","dos","como","mas","foi",
        "preços","disponíveis","ano","modelo"}
def stem_pt(w): return re.sub(r"(s|es|ns|ais|is|os|as|eis|res|mente|dade|ção|ções|ico|ica|icos|icas)$","",w)
def preprocess(txt):
    txt = re.sub(f"[{string.punctuation}]"," ",txt.lower())
    txt = re.sub(r"\d+"," ",txt)        # remova se quiser números
    return [stem_pt(t) for t in txt.split() if len(t)>2 and t not in STOP]

# ---------- motor BM25 ----------
class SearchEngine:
    def __init__(self, idx="data/indice_bm25.json", meta="data/metadados_documentos.json",
                 k1=1.5, b=0.75):
        self.idx   = json.load(open(idx, encoding="utf-8"))
        self.meta  = json.load(open(meta, encoding="utf-8"))
        self.N     = self.idx["_stats"]["N"]
        self.avgdl = self.idx["_stats"]["avgdl"]
        self.lens  = self.idx["_lens"]
        self.k1, self.b = k1, b

    def _score_query(self, query, topk):
        terms = preprocess(query)
        if not terms: return []
        scores = defaultdict(float)
        for t in terms:
            entry = self.idx.get(t)
            if not entry: continue
            idf = math.log1p((self.N - entry["df"] + .5)/(entry["df"] + .5))
            for doc, tf in entry["postings"].items():
                dl = self.lens[doc]
                denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
                scores[doc] += idf * (tf * (self.k1 + 1) / denom)
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:topk]
        return [{**self.meta[d], "score": round(s,3)} for d,s in ranked]

    # API pública
    def search(self, query, topk=10):   return self._score_query(query, topk)
    def batch (self, iterable, topk=10):
        for q in iterable: yield q.strip(), self._score_query(q, topk)

# ---------- helpers de saída ----------
def print_table(res):
    head = ["Score","Marca","Modelo","Ano","Preço","URL"]
    rows = [(r["score"], r["marca"], r["modelo"], r["ano"], r["preco"], r["url"]) for r in res]
    if TABS: print(tabulate(rows, headers=head, tablefmt="github", floatfmt=".3f"))
    else:
        for r in res:
            print(f"[{r['score']:.3f}] {r['marca']} {r['modelo']} {r['ano']}  → {r['preco']}")
            print(f"    {r['url']}")

def write_csv(lines, path, topk):
    with open(path, "w", newline='', encoding="utf-8") as f:
        w = csv.writer(f)
        header = ["consulta"] + [f"doc{i}_score" for i in range(1, topk+1)]
        w.writerow(header)
        for q, res in lines:
            flat = []
            for r in res:
                flat.append(f"{r['marca']} {r['modelo']} {r['ano']}|{r['score']}")
            while len(flat) < topk: flat.append("")   # padding
            w.writerow([q] + flat)

# ---------- main ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="*", help="consulta livre (pode ficar vazia p/ REPL)")
    ap.add_argument("-k","--topk", type=int, default=10, help="nº resultados")
    ap.add_argument("-f","--file", help="arquivo com uma consulta por linha")
    ap.add_argument("-o","--output", help="csv p/ salvar resultados do -f")
    args = ap.parse_args()
    eng = SearchEngine()

    # 1) Modo batch (arquivo)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            linhas = list(eng.batch(f, topk=args.topk))
        if args.output:
            write_csv(linhas, args.output, args.topk)
            print(f"✔ Resultados salvos em {args.output}")
        else:
            for q,res in linhas:
                print(f"\n🔍  {q}")
                print_table(res)
        sys.exit()

    # 2) Query única pelo CLI
    if args.query:
        consulta = " ".join(args.query)
        res = eng.search(consulta, topk=args.topk)
        print_table(res)
        sys.exit()

    # 3) REPL / modo interativo
    print("=== Modo interativo (digite ENTER vazio p/ sair) ===")
    while True:
        q = input("consulta> ").strip()
        if not q: break
        print_table(eng.search(q, args.topk))
