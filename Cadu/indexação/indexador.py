# -----------------------------
# IMPORTS
# -----------------------------
import json, re, time, sys
import os
from collections import defaultdict
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer

# -----------------------------
# CONFIGURAÇÕES INICIAIS
# -----------------------------
nltk.download('punkt')
nltk.download('stopwords')
stopwords_pt = set(stopwords.words('portuguese'))
stemmer = RSLPStemmer()

# -----------------------------
# FUNÇÕES DE PRÉ-PROCESSAMENTO
# -----------------------------
def limpar_texto(texto):
    texto = texto.lower()
    texto = re.sub(r'[^\w\s]', '', texto)
    return texto.strip()

def tokenizar_filtrar(texto):
    tokens = word_tokenize(limpar_texto(texto))
    return [stemmer.stem(t) for t in tokens if t not in stopwords_pt]

# -----------------------------
# EXTRAÇÃO DOS DADOS DO JSON
# -----------------------------
def extrair_descricoes(json_path):
    # Verificando se o arquivo existe
    if not os.path.exists(json_path):
        print(f"Arquivo não encontrado: {json_path}")
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        dados = json.load(f)["dados"]

    docs = []
    for modelo in dados:
        for versao in modelo["versoes"]:
            texto = modelo["modelo"] + " " + versao["versao"]
            for secao in versao["ficha_tecnica"]:
                for chave, valor in secao["dados"].items():
                    if isinstance(valor, dict):
                        texto += " " + " ".join(valor.values())
                    else:
                        texto += " " + str(valor)
            tokens = tokenizar_filtrar(texto)
            docs.append(tokens)
    return docs

# -----------------------------
# ÍNDICE INVERTIDO
# -----------------------------
def construir_indice_invertido(docs):
    indice = defaultdict(set)
    for doc_id, tokens in enumerate(docs):
        for token in set(tokens):
            indice[token].add(doc_id)
    return dict(indice)

# -----------------------------
# EXECUÇÃO PRINCIPAL
# -----------------------------
if __name__ == "__main__":
    print("🚀 Iniciando indexação...")
    
    # Verificando diretório de execução
    print("Diretório atual:", os.getcwd())

    inicio = time.time()
    
    # Ajustando o caminho para subir uma pasta e acessar o arquivo correto
    json_path = "../data/icarros_dados_completos.json"  # Caminho relativo correto
    docs = extrair_descricoes(json_path)
    
    # Verificando se documentos foram extraídos
    if not docs:
        print("Erro ao extrair documentos. Verifique o caminho do arquivo.")
        sys.exit(1)
    
    indice = construir_indice_invertido(docs)
    fim = time.time()

    print("⏱ Tempo de indexação:", round(fim - inicio, 2), "segundos")
    print("📦 Tamanho do índice (número de termos):", len(indice))
    print("💾 Memória estimada do índice:", sys.getsizeof(indice), "bytes")

    # (Opcional) salvar índice em disco
    with open("../data/indice_invertido.json", "w", encoding="utf-8") as f:
        json.dump({k: list(v) for k, v in indice.items()}, f, ensure_ascii=False, indent=4)
    print("✅ Índice invertido salvo em 'data/indice_invertido.json'")
