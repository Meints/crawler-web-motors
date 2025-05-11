import json
import re
import string
from collections import defaultdict
import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer

# Baixar recursos necessários (se ainda não tiver)
nltk.download("stopwords")

stop_words = set(stopwords.words("portuguese"))
stemmer = RSLPStemmer()

# Função de limpeza e pré-processamento de texto
def clean_text(text):
    text = text.lower()
    text = re.sub(f"[{re.escape(string.punctuation)}]", " ", text)
    tokens = re.findall(r'\b\w+\b', text)  
    tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    stems = [stemmer.stem(token) for token in tokens]
    return stems

# Carregando os dados do JSON
with open("data/carros_seminovos_com_detalhes.json", "r", encoding="utf-8") as f:
    carros = json.load(f)

inverted_index = defaultdict(set)
doc_id_map = {}
doc_counter = 0

# Construção do índice e metadados
for carro in carros:
    doc_id = f"doc_{doc_counter}"
    doc_counter += 1

    texto = " ".join([
        carro.get("titulo", ""),
        carro.get("descricao", ""),
        carro.get("preco", ""),
        carro.get("anunciante", ""),
        " ".join(f"{k} {v}" for k, v in carro.get("detalhes", {}).items())
    ])

    termos = clean_text(texto)
    for termo in termos:
        inverted_index[termo].add(doc_id)

    doc_id_map[doc_id] = {
        "titulo": carro.get("titulo", ""),
        "descricao": carro.get("descricao", ""),
        "preco": carro.get("preco", ""),
        "anunciante": carro.get("anunciante", ""),
        "link": carro.get("link", ""),
        "detalhes": carro.get("detalhes", {})
    }

# Converte sets para listas para salvar como JSON
inverted_index_json = {termo: sorted(list(docs)) for termo, docs in inverted_index.items()}

# Salva os arquivos
with open("indice_invertido.json", "w", encoding="utf-8") as f:
    json.dump(inverted_index_json, f, ensure_ascii=False, indent=2)

with open("metadados_documentos.json", "w", encoding="utf-8") as f:
    json.dump(doc_id_map, f, ensure_ascii=False, indent=2)

print("✅ Índice invertido e metadados salvos com sucesso.")
