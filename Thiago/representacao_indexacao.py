import json
import re
import string
from collections import defaultdict

# Lista manual de stopwords (versão simplificada em português)
stop_words = {
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não",
    "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi",
    "preços", "disponíveis", "ano", "modelo"
}

# Função de stemming bem simples para português
def simple_stem(word):
    return re.sub(r"(s|es|ns|ais|is|os|as|eis|res|mente|dade|ção|ções|ico|ica|icos|icas)$", "", word)

# Função de limpeza e normalização de texto
def clean_text(text):
    text = text.lower()
    text = re.sub(f"[{string.punctuation}]", " ", text)
    text = re.sub(r"\\d+", " ", text)
    tokens = text.split()
    tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    stems = [simple_stem(token) for token in tokens]
    return stems

# Função para validar tokens
def is_valid_token(token):
    return len(token) > 2 and token not in stop_words

# Carregando o JSON com os dados
with open("data/results_webmotors_full_content.json", "r", encoding="utf-8") as f:
    content = json.load(f)

inverted_index = defaultdict(set)
doc_id_map = {}
doc_counter = 0

for marca in content["dados"]:
    marca_nome = marca["marca"]
    for carro in marca["carros"]:
        modelo = carro["modelo"]
        for ano_info in carro["anos"]:
            ano = ano_info["ano"]
            preco = ano_info["preco"]
            url = ano_info["url"]
            doc_text = f"{marca_nome} {modelo} {ano} {preco}"
            terms = clean_text(doc_text)
            filtered_terms = [t for t in terms if is_valid_token(t)]
            doc_id = f"doc_{doc_counter}"
            doc_id_map[doc_id] = {
                "marca": marca_nome,
                "modelo": modelo,
                "ano": ano,
                "preco": preco,
                "url": url
            }
            for term in filtered_terms:
                inverted_index[term].add(doc_id)
            doc_counter += 1

# Convertendo sets para listas
inverted_index = {term: sorted(list(docs)) for term, docs in inverted_index.items()}

# Salvando os resultados
with open("indice_invertido.json", "w", encoding="utf-8") as f:
    json.dump(inverted_index, f, ensure_ascii=False, indent=2)

with open("metadados_documentos.json", "w", encoding="utf-8") as f:
    json.dump(doc_id_map, f, ensure_ascii=False, indent=2)

print("Arquivos gerados com sucesso: indice_invertido_melhorado.json e metadados_documentos.json")
