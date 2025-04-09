import requests
from bs4 import BeautifulSoup
import json
import os
import time
import random
from tqdm import tqdm

BASE_URL = "https://www.icarros.com.br"
JSON_PATH = "data/icarros_dados_completos.json"

# Função para baixar uma página com tentativas e tempo aleatório
def get_html(url, retries=5, wait_range=(2, 5)):
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

# Coletar links dos modelos
def coletar_links_modelos(limit=None):
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

# Coletar ficha técnica por modelo
def coletar_fichas_tecnicas_por_modelo(modelo_url):
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

# Interpretar valores das células
def interpretar_td(td):
    if 'badge-icon' in td.get("class", []):
        icon = td.find("i")
        if icon:
            if "fa-check-circle" in icon.get("class", []):
                return "possui"
            elif "fa-times-circle" in icon.get("class", []):
                return "não possui"
        return "desconhecido"
    return td.get_text(strip=True)

# Salvar incrementalmente
def salvar_incremental(dado_modelo):
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        dados_existentes = json.load(f)

    dados_existentes["dados"].append(dado_modelo)
    dados_existentes["total_modelos"] = len(dados_existentes["dados"])
    dados_existentes["paginas_acessadas"] += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dados_existentes, f, ensure_ascii=False, indent=4)

    print(f"✅ Modelo {dado_modelo['modelo']} salvo.")

# Coletar dados completos
def coletar_dados_completos(limit=None):
    modelos_urls = coletar_links_modelos(limit)

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

        for versao in tqdm(fichas, desc=f"Versões de {nome_modelo}", leave=False):
            url_ficha = versao["ficha_tecnica_url"]

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
            time.sleep(random.uniform(0.5, 1.5))

        modelo_info = {
            "modelo": nome_modelo,
            "url_modelo": url,
            "versoes": fichas
        }

        salvar_incremental(modelo_info)
        time.sleep(random.uniform(1, 2))

# Execução principal
if __name__ == "__main__":
    print("🔁 Iniciando coleta de dados do iCarros...")
    if not os.path.exists("data"):
        os.makedirs("data")

    # 🔥 Sempre sobrescreve o JSON antes de começar
    dados_iniciais = {
        "fonte": "icarros.com.br",
        "total_modelos": 0,
        "paginas_acessadas": 0,
        "dados": []
    }
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dados_iniciais, f, ensure_ascii=False, indent=4)
    print(f"🧹 Arquivo {JSON_PATH} resetado.")

    coletar_dados_completos(limit=4)  # ajuste o limit conforme necessário
    print(f"✅ Coleta finalizada. Arquivo salvo em: {JSON_PATH}")
