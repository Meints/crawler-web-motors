import json
import pandas as pd
import re
import time
import streamlit as st
from collections import defaultdict

import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Baixar stopwords se necessário
nltk.download('stopwords')

# CONFIG
ARQUIVO_JSON = 'metadados_documentos.json'
CAMPO_BUSCA = ['titulo', 'descricao', 'preco', 'anunciante']

# Pré-processamento
stop_words = set(stopwords.words('portuguese'))
stemmer = SnowballStemmer("portuguese")

def preprocess(texto):
    texto = texto.lower()
    texto = re.sub(r'[^a-zà-ú0-9\s]', '', texto)
    tokens = texto.split()
    tokens = [stemmer.stem(t) for t in tokens if t not in stop_words]
    return tokens

@st.cache_data
def carregar_dados():
    with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict):
        data = list(data.values())

    df = pd.DataFrame(data)
    df['texto'] = df[CAMPO_BUSCA].apply(lambda x: ' '.join(map(str, x)), axis=1)
    df['tokens'] = df['texto'].apply(preprocess)
    df['texto_limpo'] = df['tokens'].apply(lambda tokens: ' '.join(tokens))

    vectorizer = TfidfVectorizer(max_features=1000)
    X = vectorizer.fit_transform(df['texto_limpo'])

    return df, vectorizer, X

def buscar(query, vectorizer, X, df, top_k=5):
    tokens = preprocess(query)
    if not tokens:
        return []

    consulta = ' '.join(tokens)
    vec_query = vectorizer.transform([consulta])
    scores = cosine_similarity(vec_query, X).flatten()

    indices_ordenados = scores.argsort()[::-1]
    resultados = [(i, scores[i]) for i in indices_ordenados if scores[i] > 0][:top_k]
    return resultados

# Streamlit UI
st.set_page_config(page_title="🔍 Buscador de Seminovos", layout="wide")
st.title("🔍 Buscador de Carros Seminovos")

df, vectorizer, X = carregar_dados()

consulta = st.text_input("Digite sua busca (ex: Corolla automático 2015):")

if consulta:
    resultados = buscar(consulta, vectorizer, X, df)

    if resultados:
        st.subheader(f"🔎 {len(resultados)} resultado(s) mais relevantes:")
        for idx, score in resultados:
            carro = df.iloc[idx]
            st.markdown(f"### [{carro['titulo']}]({carro.get('link', '#')}) - {carro['preco']}")
            st.markdown(f"**{carro['descricao']}** — {carro['anunciante']}")
            st.markdown(f"📊 Relevância: `{score:.4f}`")
            if 'detalhes' in carro and isinstance(carro['detalhes'], dict):
                with st.expander("🔧 Detalhes do carro"):
                    for k, v in carro['detalhes'].items():
                        st.markdown(f"• **{k.capitalize()}**: {v}")
            st.markdown("---")
    else:
        st.warning("Nenhum resultado encontrado para sua busca.")
