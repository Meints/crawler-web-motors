import requests
from bs4 import BeautifulSoup
import json
from tqdm import tqdm
import time
import os
import random

BASE_URL = "https://www.icarros.com.br"
JSON_PATH = "icarros_dados_completos.json"

# Requisição com retries e delay aleatório
def get_html(url, retries=3, wait_range=(1, 3)):
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Erro HTTP {response.status_code} para URL: {url}")
        except Exception as e:
            print(f"Tentativa {attempt+1} falhou com erro: {e}")
        time.sleep(random.uniform(*wait_range))
    return None

# Coleta os links dos modelos
def coletar_links_modelos(limit=3):
    url = f"{BASE_URL}/catalogo/listaversoes.jsp"
    html = get_html(url)
    if not html:
        print("Erro ao acessar catálogo de versões.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("a", class_="card--review__cta")

    modelos = []
    for card in cards[:limit]:
        href = card.get("href")
        if href:
            modelos.append(BASE_URL + href)

    return modelos

# Coleta versões e links da ficha técnica
def coletar_fichas_tecnicas_por_modelo(modelo_url):
    html = get_html(modelo_url)
    if not html:
        print(f"Erro ao acessar a página do modelo: {modelo_url}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    versoes = soup.select("div.dropdown-checkbox__label a")

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

# Interpreta ícones e textos nas células
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

# Coleta tudo e salva como JSON
def coletar_dados_completos(limit=3):
    modelos_urls = coletar_links_modelos(limit)
    dados_modelos = []
    paginas_acessadas = 0

    for url in modelos_urls:
        print(f"📦 Coletando modelo: {url}")
        nome_modelo = url.split("/")[-1].capitalize()
        fichas = coletar_fichas_tecnicas_por_modelo(url)
        paginas_acessadas += 1  # Página do modelo

        for versao in tqdm(fichas, desc=f"Versões de {nome_modelo}", leave=False):
            url_ficha = versao["ficha_tecnica_url"]
            html = get_html(url_ficha)
            if not html:
                continue

            paginas_acessadas += 1  # Página da ficha
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
            time.sleep(0.5)

        dados_modelos.append({
            "modelo": nome_modelo,
            "url_modelo": url,
            "versoes": fichas
        })
        time.sleep(random.uniform(1, 2))

    return {
        "fonte": "icarros.com.br",
        "total_modelos": len(dados_modelos),
        "paginas_acessadas": paginas_acessadas,
        "dados": dados_modelos
    }

# Execução principal
if __name__ == "__main__":
    print("🔁 Iniciando coleta de dados do iCarros...")
    dados_finais = coletar_dados_completos(limit=3)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(dados_finais, f, ensure_ascii=False, indent=4)

    print(f"✅ Coleta finalizada. Arquivo salvo em: {JSON_PATH}")
