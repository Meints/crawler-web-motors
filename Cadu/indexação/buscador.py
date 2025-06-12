import streamlit as st
import json
import re
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer

# --------------------------
# NLTK setup
# --------------------------
nltk.download('punkt')
nltk.download('stopwords')
stopwords_pt = set(stopwords.words('portuguese'))
stemmer = RSLPStemmer()

# --------------------------
# Funções de pré-processamento
# --------------------------
def limpar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    return texto.strip()

def tokenizar_filtrar(texto):
    tokens = word_tokenize(limpar_texto(texto))
    return [stemmer.stem(t) for t in tokens if t not in stopwords_pt]

# --------------------------
# Carregamento de dados
# --------------------------
@st.cache_data
def carregar_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

@st.cache_data
def carregar_dados(dados_json):
    docs_raw = []
    for modelo in dados_json["dados"]:
        for versao in modelo["versoes"]:
            docs_raw.append({
                "modelo": modelo["modelo"],
                "versao": versao["versao"],
                "url_ficha": versao.get("ficha_tecnica_url", "")
            })
    return docs_raw

@st.cache_data
def carregar_indice(path):
    with open(path, 'r', encoding='utf-8') as f:
        bruto = json.load(f)
    return {k: set(v) for k, v in bruto.items()}

# --------------------------
# Função de busca
# --------------------------
def buscar(termo, indice, docs_raw):
    termo_proc = stemmer.stem(limpar_texto(termo))
    doc_ids = indice.get(termo_proc, set())
    resultados = []
    for doc_id in doc_ids:
        doc = docs_raw[doc_id]
        texto_completo = f"{doc['modelo']} {doc['versao']}".lower()
        if termo.lower() in texto_completo:
            resultados.append((doc_id, doc))
    return resultados

# --------------------------
# Interface Streamlit
# --------------------------
st.set_page_config(page_title="Buscador de Carros", layout="wide")
st.title("🚘 Buscador de Carros - iCarros")

# Arquivos
caminho_dados = "../data/icarros_dados_completos.json"
caminho_indice = "../data/indice_invertido.json"

# Carregar dados
dados_json = carregar_json(caminho_dados)
docs_raw = carregar_dados(dados_json)
indice = carregar_indice(caminho_indice)

# Campo de busca
termo_busca = st.text_input("🔍 Digite o nome de um carro ou termo técnico:")

# Buscar e exibir resultados
if termo_busca:
    resultados = buscar(termo_busca, indice, docs_raw)

    if resultados:
        st.subheader(f"{len(resultados)} resultado(s) encontrado(s):")

        for _, doc in resultados:
            modelo = doc["modelo"]
            versao = doc["versao"]
            url = doc["url_ficha"]
            st.markdown(f"### 🚗 {modelo} - {versao}")
            if url:
                st.markdown(f"[🔗 Ver ficha técnica no iCarros]({url})", unsafe_allow_html=True)
            st.markdown("---")
    else:
        st.warning("Nenhum resultado encontrado.")
else:
    st.info("Digite um termo acima para iniciar a busca.")
