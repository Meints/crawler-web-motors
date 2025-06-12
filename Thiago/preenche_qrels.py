"""
Gera um esboço de qrels.csv com os top-5 resultados
para cada query de queries.txt. Depois basta editar o
campo `rel` (0 = irrelevante, 1 = relevante) manualmente.
"""
import csv, pandas as pd
from search import SearchEngine   # seu motor BM25

TOPK = 5
engine = SearchEngine()

# 1) carrega queries.txt
with open("queries.txt", encoding="utf-8") as f:
    queries = [q.strip() for q in f if q.strip()]

rows = []
for q in queries:
    res = engine.search(q, topk=TOPK)
    for r in res:
        rows.append([q, r["url"], ""])

# 2) grava qrels_skel.csv
with open("qrels_skel.csv", "w", newline='', encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["query","doc_id","rel"])
    w.writerows(rows)

print("Arquivo qrels_skel.csv gerado. Agora abra-o e marque o campo rel (0/1).")
