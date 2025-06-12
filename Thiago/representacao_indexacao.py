import json, re, string, math
from collections import defaultdict, Counter

# ------------------------ utilidades de texto ------------------------
stop_words = {
    "de","a","o","que","e","do","da","em","um","para","é","com","não",
    "uma","os","no","se","na","por","mais","as","dos","como","mas","foi",
    "preços","disponíveis","ano","modelo"
}
def simple_stem(word):
    return re.sub(r"(s|es|ns|ais|is|os|as|eis|res|mente|dade|ção|ções|ico|ica|icos|icas)$", "", word)

def clean_text(txt):
    txt = txt.lower()
    txt = re.sub(f"[{string.punctuation}]", " ", txt)
    txt = re.sub(r"\d+", " ", txt)
    tokens = txt.split()
    return [simple_stem(t) for t in tokens if len(t) > 2 and t not in stop_words]
# ---------------------------------------------------------------------

# ---------- leitura do JSON bruto (ajuste o caminho se precisar) -----
with open("data/results_webmotors_full_content.json", encoding="utf-8") as f:
    raw = json.load(f)
# ---------------------------------------------------------------------

inverted = defaultdict(lambda: {"postings": {}})  # termo → {df, postings{doc:tf}}
doc_meta   = {}          # doc_id → marca/modelo/ano/preço/url
doc_len    = {}          # doc_id → |D|
doc_id     = 0

for marca in raw["dados"]:
    m_nome = marca["marca"]
    for carro in marca["carros"]:
        modelo = carro["modelo"]
        for ano_info in carro["anos"]:
            ano, preco, url = ano_info["ano"], ano_info["preco"], ano_info["url"]

            text = f"{m_nome} {modelo} {ano} {preco}"
            terms = clean_text(text)
            tf    = Counter(terms)
            if not tf:     # documento vazio? pula
                continue

            did = f"doc_{doc_id}"
            doc_id += 1

            # guarda metadados e tamanho
            doc_meta[did] = {"marca": m_nome, "modelo": modelo,
                             "ano": ano, "preco": preco, "url": url}
            doc_len[did]  = sum(tf.values())

            # atualiza índice invertido
            for term, freq in tf.items():
                inverted[term]["postings"][did] = freq

# calcula df para cada termo
for term, entry in inverted.items():
    entry["df"] = len(entry["postings"])

# estatísticas globais
N      = len(doc_meta)
avgdl  = sum(doc_len.values()) / N

inverted["_stats"] = {"N": N, "avgdl": avgdl}
inverted["_lens"]  = doc_len           # comprimento de cada documento

# --------------------- grava arquivos ---------------------
with open("data/indice_bm25.json", "w", encoding="utf-8") as f:
    json.dump(inverted, f, ensure_ascii=False, indent=2)

with open("data/metadados_documentos.json", "w", encoding="utf-8") as f:
    json.dump(doc_meta, f, ensure_ascii=False, indent=2)

print(f"Índice gerado com {len(inverted)-2} termos e {N} documentos ✅")
print(f"avgdl = {avgdl:.2f}")
