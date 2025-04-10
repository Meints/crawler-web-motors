import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
from tqdm import tqdm

# Constantes para o projeto
BASE_URL = "https://www.icarros.com.br"
JSON_PATH = "data/icarros_dados_completos.json"
SUPORTE_PATH = "data/versoes_processadas.json"

def get_html(url, retries=5, wait_range=(2, 5)):
    """
    Tenta obter o HTML de uma URL com tentativas e espera entre elas.
    
    Args:
        url (str): URL da página para buscar.
        retries (int): Número máximo de tentativas.
        wait_range (tuple): Intervalo de espera aleatória entre tentativas.
    
    Returns:
        str or None: HTML da página ou None se falhar.
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
            elif response.status_code == 405:
                print(f"⚠️ Erro 405 em {url}")
            else:
                print(f"❌ Erro {response.status_code} para URL: {url}")
        except requests.exceptions.Timeout:
            print(f"⏰ Timeout na tentativa {attempt + 1} para {url}")
        except Exception as e:
            print(f"⚠️ Erro na tentativa {attempt + 1}: {e}")
        time.sleep(random.uniform(*wait_range))
    print(f"❌ Falha ao acessar {url} após {retries} tentativas.")
    return None

def resetar_suporte():
    """
    Reseta o arquivo de suporte, criando um JSON vazio para versões processadas.
    """
    dados_iniciais = {"versoes": []}
    with open(SUPORTE_PATH, "w", encoding="utf-8") as f:
        json.dump(dados_iniciais, f, ensure_ascii=False, indent=4)
    print(f"🧹 Arquivo {SUPORTE_PATH} resetado.")

def inicializar_json_principal_e_suporte():
    """
    Inicializa o JSON principal e o arquivo de suporte, caso ainda não existam.
    """
    if not os.path.exists(JSON_PATH):
        dados_iniciais = {
            "fonte": "icarros.com.br",
            "total_modelos": 0,
            "paginas_acessadas": 0,
            "dados": []
        }
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(dados_iniciais, f, ensure_ascii=False, indent=4)
        print(f"🧹 Arquivo {JSON_PATH} criado (não existia).")
        resetar_suporte()
    else:
        print(f"ℹ️ Arquivo {JSON_PATH} já existe. Não será resetado.")
        if not os.path.exists(SUPORTE_PATH):
            resetar_suporte()

def carregar_versoes_processadas():
    """
    Carrega o JSON de suporte contendo as versões já processadas.

    Returns:
        dict: Dados do arquivo de suporte.
    """
    with open(SUPORTE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_versao_processada(nome, url):
    """
    Salva uma nova versão processada no suporte.

    Args:
        nome (str): Nome da versão.
        url (str): URL da ficha técnica da versão.
    """
    dados = carregar_versoes_processadas()
    registro = {"versao": nome, "url": url}
    if registro not in dados["versoes"]:
        dados["versoes"].append(registro)
        with open(SUPORTE_PATH, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=4)
        print(f"✅ Versão '{nome}' registrada no suporte.")
    else:
        print(f"ℹ️ Versão '{nome}' já consta no suporte.")

def coletar_links_modelos(limit=None):
    """
    Coleta todos os links dos modelos disponíveis no site.

    Args:
        limit (int, optional): Limita a quantidade de modelos coletados.

    Returns:
        list: Lista de URLs dos modelos.
    """
    modelos = []
    pagina = 1

    while True:
        url = f"{BASE_URL}/catalogo/listaversoes.jsp?bid=2&app=18&sop=seg_0.1_-cur_t.1_&pas=1&lis=0&pag={pagina}&ord=4"
        html = get_html(url)
        if not html:
            break

        soup = BeautifulSoup(html, "html.parser")
        cards = soup.find_all("a", class_="card--review__cta")
        print(f"🔎 Página {pagina} - {len(cards)} modelos encontrados.")

        if not cards:
            break

        for card in cards:
            href = card.get("href")
            if href:
                modelos.append(BASE_URL + href)
                if limit and len(modelos) >= limit:
                    return modelos[:limit]

        pagina += 1
        time.sleep(random.uniform(1, 2))

    return modelos

def coletar_fichas_tecnicas_por_modelo(modelo_url):
    """
    Coleta as fichas técnicas de todas as versões de um modelo.

    Args:
        modelo_url (str): URL do modelo.

    Returns:
        list: Lista de dicionários com nome da versão e URL da ficha técnica.
    """
    html = get_html(modelo_url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    versoes = soup.select("div.dropdown-checkbox__label a")

    if not versoes:
        return []

    links_ficha_tecnica = []
    for versao in versoes:
        nome = versao.get_text(strip=True)
        href = versao.get("href")
        if href:
            links_ficha_tecnica.append({
                "versao": nome,
                "ficha_tecnica_url": BASE_URL + href
            })
    return links_ficha_tecnica

def interpretar_td(td):
    """
    Interpreta uma célula de tabela, tratando ícones de presença/ausência.

    Args:
        td (bs4.element.Tag): Elemento <td> da tabela.

    Returns:
        str: Valor interpretado da célula.
    """
    if 'badge-icon' in td.get("class", []):
        icon = td.find("i")
        if icon:
            if "fa-check-circle" in icon.get("class", []):
                return "possui"
            elif "fa-times-circle" in icon.get("class", []):
                return "não possui"
        return "desconhecido"
    return td.get_text(strip=True)

def salvar_incremental(dado_modelo):
    """
    Salva incrementalmente os dados de um modelo no JSON principal.

    Args:
        dado_modelo (dict): Dados do modelo a serem salvos.
    """
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        dados_existentes = json.load(f)

    dados_existentes["dados"].append(dado_modelo)
    dados_existentes["total_modelos"] = len(dados_existentes["dados"])
    dados_existentes["paginas_acessadas"] += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dados_existentes, f, ensure_ascii=False, indent=4)

    print(f"✅ Modelo {dado_modelo['modelo']} salvo no JSON principal.")

def coletar_dados_completos(limit=None):
    """
    Processo principal de coleta de dados de todos os modelos e suas versões.

    Args:
        limit (int, optional): Limite de modelos para coletar.
    """
    modelos_urls = coletar_links_modelos(limit)
    suporte = carregar_versoes_processadas()

    for url in modelos_urls:
        print(f"\n📦 Coletando modelo: {url}")
        nome_modelo = url.split("/")[-1].capitalize()
        fichas = coletar_fichas_tecnicas_por_modelo(url)

        if not fichas:
            print(f"🚫 Modelo {nome_modelo} sem versões. Pulando...")
            modelo_info = {
                "modelo": nome_modelo,
                "url_modelo": url,
                "versoes": []
            }
            salvar_incremental(modelo_info)
            continue

        novas_versoes = []
        for versao in tqdm(fichas, desc=f"Versões de {nome_modelo}", leave=False):
            nome_versao = versao["versao"]
            url_ficha = versao["ficha_tecnica_url"]

            registro = {"versao": nome_versao, "url": url_ficha}
            if registro in suporte["versoes"]:
                print(f"ℹ️ Versão '{nome_versao}' já processada. Ignorando...")
                continue

            # Garantir que obtenha o HTML da ficha técnica
            while True:
                html = get_html(url_ficha)
                if html:
                    break
                print(f"🔁 Tentando novamente {url_ficha}")
                time.sleep(random.uniform(2, 4))

            soup = BeautifulSoup(html, "html.parser")
            titulos = soup.find_all("p", class_="subtitle__onLight")
            tabelas = soup.find_all("table", class_="table table-bordered bg-white")

            secoes = []
            for titulo, tabela in zip(titulos, tabelas):
                secao_nome = titulo.get_text(strip=True)
                secao_dados = {}

                for row in tabela.find_all("tr"):
                    cols = row.find_all("td")
                    col_data = [interpretar_td(td) for td in cols]
                    if len(col_data) == 2:
                        secao_dados[col_data[0]] = col_data[1]
                    elif len(col_data) == 3:
                        secao_dados[col_data[0]] = {
                            "opcao_1": col_data[1],
                            "opcao_2": col_data[2]
                        }

                secoes.append({
                    "titulo": secao_nome,
                    "dados": secao_dados
                })

            versao["ficha_tecnica"] = secoes
            novas_versoes.append(versao)
            salvar_versao_processada(nome_versao, url_ficha)
            suporte["versoes"].append(registro)

            time.sleep(random.uniform(0.5, 1.5))

        if novas_versoes:
            modelo_info = {
                "modelo": nome_modelo,
                "url_modelo": url,
                "versoes": novas_versoes
            }
            salvar_incremental(modelo_info)
        else:
            print(f"ℹ️ Não há novas versões para o modelo {nome_modelo}. JSON principal não será alterado.")
        time.sleep(random.uniform(1, 2))

# Execução principal
if __name__ == "__main__":
    print("🔁 Iniciando coleta de dados do iCarros...")

    if not os.path.exists("data"):
        os.makedirs("data")

    inicializar_json_principal_e_suporte()
    coletar_dados_completos(limit=None)

    print(f"✅ Coleta finalizada. Arquivo principal salvo em: {JSON_PATH}")
