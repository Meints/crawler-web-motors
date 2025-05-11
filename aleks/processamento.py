import os
import json
import time
import sys
import psutil
from collections import defaultdict
import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer
import string

# Baixar recursos do NLTK se necessário
nltk.download('stopwords', quiet=True)
nltk.download('rslp', quiet=True)


# Caminhos dos arquivos
DIRETORIO_DADOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
ARQUIVO_JSON = os.path.join(DIRETORIO_DADOS, 'anuncios.json')
ARQUIVO_INDICE = os.path.join(DIRETORIO_DADOS, 'indice_invertido.json')

# Parâmetros de granularidade e chunk
GRANULARIDADE = 'campo'  # 'anuncio' ou 'campo' (campo = marca, modelo, etc)
TAMANHO_CHUNK = 100  # Quantidade de anúncios por chunk

# Função para medir uso de memória
def uso_memoria_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

# Função de limpeza e pré-processamento
class Preprocessador:
    def __init__(self):
        self.stopwords = set(stopwords.words('portuguese'))
        self.stemmer = RSLPStemmer()
        self.tabela_pontuacao = str.maketrans('', '', string.punctuation)

    def limpar_texto(self, texto):
        if not texto:
            return ''
        texto = texto.lower()
        texto = texto.translate(self.tabela_pontuacao)
        return texto

    def analisar_lexica(self, texto):
        tokens = texto.split()
        tokens = [t for t in tokens if t not in self.stopwords]
        tokens = [self.stemmer.stem(t) for t in tokens]
        return tokens

# Função para carregar dados
def carregar_anuncios():
    with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
        return json.load(f)

# Função para categorizar preço em faixas
def faixa_preco(preco):
    if not preco:
        return None
    preco = str(preco).replace('R$', '').replace('.', '').replace(',', '.').strip()
    try:
        preco = float(preco)
    except Exception:
        return None
    if preco < 20000:
        return '0-20k'
    elif preco < 40000:
        return '20k-40k'
    elif preco < 60000:
        return '40k-60k'
    elif preco < 100000:
        return '60k-100k'
    else:
        return '100k+'

# Função para categorizar quilometragem em faixas
def faixa_km(km):
    if not km:
        return None
    km = str(km).replace('.', '').replace('km', '').strip()
    try:
        km = int(km)
    except Exception:
        return None
    if km < 50000:
        return '0-50k'
    elif km < 100000:
        return '50k-100k'
    elif km < 150000:
        return '100k-150k'
    elif km < 200000:
        return '150k-200k'
    else:
        return '200k+'

# Função para categorizar ano em faixas
def faixa_ano(ano):
    if not ano:
        return None
    try:
        ano = int(ano)
    except Exception:
        return None
    if ano < 2000:
        return '-2000'
    elif ano < 2010:
        return '2000-2009'
    elif ano < 2020:
        return '2010-2019'
    else:
        return '2020+'

# Função para construir índice invertido melhorado
# Indexa todos os campos relevantes, com faixas para preço, km e ano

def construir_indice_invertido(anuncios, granularidade='campo', chunk_size=100):
    campos_texto = [
        'marca', 'modelo', 'estado', 'categoria', 'tipo_veiculo', 'potencia',
        'combustivel', 'cambio', 'direcao', 'cor', 'portas', 'gnv', 'final_placa'
    ]
    indice = defaultdict(set)
    preprocessador = Preprocessador()
    total = len(anuncios)
    for i in range(0, total, chunk_size):
        chunk = anuncios[i:i+chunk_size]
        for anuncio in chunk:
            id_anuncio = anuncio.get('id')
            # Indexação de campos textuais
            for campo in campos_texto:
                valor = anuncio.get(campo)
                if valor:
                    texto_limpo = preprocessador.limpar_texto(str(valor))
                    tokens = preprocessador.analisar_lexica(texto_limpo)
                    for token in tokens:
                        indice[f'{campo}:{token}'].add(id_anuncio)
            # Indexação de preço por faixa
            faixa = faixa_preco(anuncio.get('preco'))
            if faixa:
                indice[f'preco:{faixa}'].add(id_anuncio)
            # Indexação de quilometragem por faixa
            faixa = faixa_km(anuncio.get('quilometragem'))
            if faixa:
                indice[f'quilometragem:{faixa}'].add(id_anuncio)
            # Indexação de ano por faixa
            faixa = faixa_ano(anuncio.get('ano'))
            if faixa:
                indice[f'ano:{faixa}'].add(id_anuncio)
    # Converte sets para listas para serialização
    return {k: list(v) for k, v in indice.items()}

# Função principal
if __name__ == '__main__':
    print('Iniciando processamento...')
    t0 = time.time()
    mem0 = uso_memoria_mb()

    anuncios = carregar_anuncios()
    print(f'Total de anúncios carregados: {len(anuncios)}')

    indice = construir_indice_invertido(anuncios, granularidade=GRANULARIDADE, chunk_size=TAMANHO_CHUNK)

    # Salvar índice invertido
    with open(ARQUIVO_INDICE, 'w', encoding='utf-8') as f:
        json.dump(indice, f, ensure_ascii=False, indent=2)

    t1 = time.time()
    mem1 = uso_memoria_mb()
    tamanho_indice = os.path.getsize(ARQUIVO_INDICE) / 1024  # KB

    print(f'Processamento concluído em {t1-t0:.2f} segundos.')
    print(f'Uso de memória: {mem1-mem0:.2f} MB')
    print(f'Tamanho do índice invertido: {tamanho_indice:.2f} KB')
    print(f'Granularidade: {GRANULARIDADE}, Chunk: {TAMANHO_CHUNK}')
    print(f'Total de termos no índice: {len(indice)}')

    # Salvar métricas em arquivo JSON
    ARQUIVO_METRICAS = os.path.join(DIRETORIO_DADOS, 'metricas_processamento.json')
    metricas = {
        'tempo_processamento_segundos': round(t1-t0, 2),
        'uso_memoria_mb': round(mem1-mem0, 2),
        'tamanho_indice_kb': round(tamanho_indice, 2),
        'granularidade': GRANULARIDADE,
        'chunk': TAMANHO_CHUNK,
        'total_termos_indice': len(indice),
        'total_anuncios': len(anuncios)
    }
    with open(ARQUIVO_METRICAS, 'w', encoding='utf-8') as f:
        json.dump(metricas, f, ensure_ascii=False, indent=2)
    print(f'Métricas salvas em {ARQUIVO_METRICAS}') 