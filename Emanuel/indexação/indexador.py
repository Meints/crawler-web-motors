import json
import re
import string
from collections import defaultdict

# Lista manual de stopwords (versão simplificada em português)
stop_words = {
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não",
    "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi",
    "preços", "disponíveis", "ano", "modelo", "km", "r$", "|", "flex", "1.0" # Adicionando termos comuns nos seus dados
}

# Função de stemming bem simples para português
def simple_stem(word):
    return re.sub(r"(s|es|ns|ais|is|os|as|eis|res|mente|dade|ção|ções|ico|ica|icos|icas)$", "", word)

# Função de limpeza e normalização de texto
def clean_text(text):
    text = text.lower()
    text = re.sub(f"[{string.punctuation}]", " ", text)
    text = re.sub(r"\d+", " ", text) # Removendo números também
    tokens = text.split()
    tokens = [t for t in tokens if t not in stop_words and len(t) > 2]
    stems = [simple_stem(token) for token in tokens]
    return stems

# Função para validar tokens
def is_valid_token(token):
    return len(token) > 2 and token not in stop_words

# Carregando o JSON com os dados
try:
    with open("carros_localiza_completo.json", "r", encoding="utf-8") as f:
        dados = json.load(f)
except FileNotFoundError:
    print("Erro: O arquivo 'carros_localiza_completo.json' não foi encontrado.")
    exit()

inverted_index = defaultdict(set)
doc_id_map = {}
doc_counter = 0

for carro in dados:
    if carro: # Verifica se o objeto não está vazio
        marca = carro.get("marca", "").strip()
        modelo = carro.get("modelo", "").strip()
        km = carro.get("km", "").replace(" km |", "").strip()
        ano = carro.get("ano", "").replace(" |", "").strip()
        cambio = carro.get("cambio", "").strip()
        preco_de = carro.get("preco_de", "").replace("R$", "").strip()
        preco = carro.get("preco", "").replace("R$", "").strip()
        local = carro.get("local", "").strip()
        link = carro.get("link", "").strip()

        doc_text = f"{marca} {modelo} {km} {ano} {cambio} {preco_de} {preco} {local}"
        terms = clean_text(doc_text)
        filtered_terms = [t for t in terms if is_valid_token(t)]
        doc_id = f"doc_{doc_counter}"
        doc_id_map[doc_id] = {
            "marca": marca,
            "modelo": modelo,
            "km": km,
            "ano": ano,
            "cambio": cambio,
            "preco_de": preco_de,
            "preco": preco,
            "local": local,
            "link": link
        }
        for term in filtered_terms:
            inverted_index[term].add(doc_id)
        doc_counter += 1

# Convertendo sets para listas
inverted_index = {term: sorted(list(docs)) for term, docs in inverted_index.items()}

# Salvando os resultados
with open("indice_invertido_localiza_simples.json", "w", encoding="utf-8") as f:
    json.dump(inverted_index, f, ensure_ascii=False, indent=2)

with open("metadados_documentos_localiza_simples.json", "w", encoding="utf-8") as f:
    json.dump(doc_id_map, f, ensure_ascii=False, indent=2)

print("Arquivos gerados com sucesso: indice_invertido_localiza_simples.json e metadados_documentos_localiza_simples.json")