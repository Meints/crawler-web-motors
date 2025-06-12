import json
import pandas as pd
import re
import time
import sys
from collections import defaultdict

import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from sklearn.feature_extraction.text import TfidfVectorizer

# Baixar recursos do NLTK
nltk.download('stopwords')

# CONFIGS
ARQUIVO_JSON = 'carros_seminovos_com_detalhes.json'
CAMPO_BUSCA = ['titulo', 'descricao']
MAX_FEATURES = 1000  # granularidade (você pode testar outros valores)

# Funções de pré-processamento
stop_words = set(stopwords.words('portuguese'))
stemmer = SnowballStemmer("portuguese")

def preprocess(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-zà-ú0-9\s]', '', texto)
    tokens = texto.split()
    tokens = [stemmer.stem(t) for t in tokens if t not in stop_words]
    return tokens

# Leitura do JSON
with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data)

# Texto base para representação vetorial
df['texto'] = df[CAMPO_BUSCA].apply(lambda x: ' '.join(map(str, x)), axis=1)
df['tokens'] = df['texto'].apply(preprocess)
df['texto_limpo'] = df['tokens'].apply(lambda tokens: ' '.join(tokens))

# --- TF-IDF Vetorização ---
print("\nVetorizando documentos com TF-IDF...")
start_vec = time.time()

vectorizer = TfidfVectorizer(max_features=MAX_FEATURES)
X = vectorizer.fit_transform(df['texto_limpo'])

end_vec = time.time()
print(f"TF-IDF concluído em {end_vec - start_vec:.2f} segundos")
print(f"Dimensão: {X.shape} (docs x termos)")
print(f"Espaço ocupado (sparse): {X.data.nbytes / 1024:.2f} KB")

# --- Índice Invertido Tradicional ---
print("\nIndexando com índice invertido...")
start_inv = time.time()
inverted_index = defaultdict(set)

for idx, tokens in enumerate(df['tokens']):
    for token in tokens:
        inverted_index[token].add(idx)

end_inv = time.time()
print(f"Indexação concluída em {end_inv - start_inv:.2f} segundos")
print(f"Tamanho do índice: {len(inverted_index)} termos")

# --- Exportar dados limpos para JSON ---
OUTPUT_JSON = 'carros_seminovos_limpos.json'
df_export = df[['titulo', 'descricao', 'preco', 'tokens', 'texto_limpo']]
df_export.to_json(OUTPUT_JSON, orient='records', force_ascii=False, indent=2)
print(f"\nDados limpos exportados para '{OUTPUT_JSON}' com sucesso.")

# --- Busca interativa (AND) ---
print("\nDigite termos para buscar veículos (digite 'sair' para encerrar):")
while True:
    consulta = input("> ")
    if consulta.lower() in ('sair', 'exit', 'q'):
        break

    tokens_consulta = preprocess(consulta)
    resultados = None

    for token in tokens_consulta:
        if token in inverted_index:
            if resultados is None:
                resultados = inverted_index[token].copy()
            else:
                resultados &= inverted_index[token]
        else:
            resultados = set()
            break

    if resultados:
        print(f"\n{len(resultados)} resultados encontrados:")
        for i in resultados:
            print(f"- {df.iloc[i]['titulo']} | {df.iloc[i]['descricao']} | {df.iloc[i]['preco']}")
    else:
        print("Nenhum resultado encontrado.")
