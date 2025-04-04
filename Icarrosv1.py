import requests
from bs4 import BeautifulSoup
import json
import time
import random

BASE_URL = "https://www.icarros.com.br"

def get_html(url, retries=3, wait_range=(1, 3)):
    """
    Função para fazer requisição HTTP com retries e delays simulando comportamento humano.
    """
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.text
            else:
                print(f"Erro HTTP {response.status_code} para URL: {url}")
        except Exception as e:
            print(f"Tentativa {attempt+1} falhou com erro: {e}")
        attempt += 1
        time.sleep(random.uniform(*wait_range))
    return None

def coletar_links_modelos(limit=3):
    """
    Coleta os primeiros N links dos modelos da página principal do catálogo iCarros.
    """
    url = f"{BASE_URL}/catalogo/listaversoes.jsp"
    html = get_html(url)
    if not html:
        print("Erro ao acessar catálogo de versões.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("a", class_="card--review__cta")
    
    modelos = []
    for card in cards[:limit]:  # Limitar para testes
        href = card.get("href")
        if href:
            modelos.append(BASE_URL + href)

    return modelos

def coletar_fichas_tecnicas_por_modelo(modelo_url):
    """
    Acessa a página de um modelo (ex: Onix) e coleta todas as versões (fichas técnicas).
    """
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

def coletar_dados_gerais():
    """
    Função principal que organiza a coleta completa:
    - Modelos do catálogo
    - Versões e links de ficha técnica por modelo
    """
    modelos_urls = coletar_links_modelos(limit=3)

    dados = []
    for url in modelos_urls:
        print(f"📦 Coletando dados do modelo: {url}")
        nome_modelo = url.split("/")[-1].capitalize()
        fichas = coletar_fichas_tecnicas_por_modelo(url)
        dados.append({
            "modelo": nome_modelo,
            "url_modelo": url,
            "versoes": fichas
        })
        time.sleep(random.uniform(2, 4))
    
    resultado_final = {
        "fonte": "icarros.com.br",
        "total_modelos": len(dados),
        "dados": dados
    }

    with open("icarros_dados_completos.json", "w", encoding="utf-8") as f:
        json.dump(resultado_final, f, ensure_ascii=False, indent=4)
    print("✅ Dados salvos em 'icarros_dados_completos.json'")

if __name__ == "__main__":
    coletar_dados_gerais()
