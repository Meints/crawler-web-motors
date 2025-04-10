import time
import json
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

def carregar_todos_os_anuncios(driver, delay=5, max_clicks=550):  
    clicks = 0
    while clicks < max_clicks:
        try:
            botao = WebDriverWait(driver, delay).until(
                EC.presence_of_element_located((By.CLASS_NAME, "btn-mais-anuncios"))
            )
            print(f"🖱️ Clicando em 'Carregar mais anúncios'... ({clicks + 1})")
            driver.execute_script("arguments[0].click();", botao)
            time.sleep(delay)
            clicks += 1
        except:
            print("✅ Não há mais botão 'Carregar mais anúncios'.")
            break

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    anuncios_div = soup.find("div", class_="anuncios")
    if not anuncios_div:
        print("❌ Div 'anuncios' não encontrada.")
        return soup, []

    carros = anuncios_div.find_all("div", class_="anuncio-thumb-new")
    print(f"🚗 Total de carros encontrados: {len(carros)}")
    return soup, carros

def extrair_detalhes_carro(driver, url):
    print(f"🔎 Acessando detalhes: {url}")
    driver.get(url)
    time.sleep(5)
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    detalhes_div = soup.find("div", class_="part-items-detalhes-icones")
    detalhes = {}

    if detalhes_div:
        items = detalhes_div.find_all("div", class_="item")
        for item in items:
            campo_div = item.find("div", class_="campo")
            valor_span = item.find("span", class_="valor")
            if campo_div and valor_span:
                campo = campo_div.get_text(strip=True).lower()
                valor = valor_span.get_text(strip=True)
                detalhes[campo] = valor
    else:
        print("⚠️ Detalhes não encontrados.")
    return detalhes

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

    driver = uc.Chrome(options=chrome_options)

    url = "https://seminovos.com.br/carros"
    driver.get(url)
    time.sleep(7)

    soup, carros = carregar_todos_os_anuncios(driver, max_clicks=550)
    # Você também pode limitar o número de cliques ao carregar anúncios para não esperar todos os cliques.
    # carros = carros[:20]  # 👈 Caso queira, descomente e limite para poucos carros.
    # 🔍 Carregar JSON existente, se houver
    json_path = "data/carros_seminovos_com_detalhes.json"
    resultados = []
    links_existentes = set()

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                resultados = json.load(f)
                links_existentes = set(carro["link"] for carro in resultados if "link" in carro)
            except json.JSONDecodeError:
                print("⚠️ Erro ao ler JSON existente. Será sobrescrito.")

    for idx, carro in enumerate(carros):
        content = carro.find("div", class_="content border-plano-nitro")
        if not content:
            continue

        preco_div = content.find("div", class_="value")
        preco = preco_div.get_text(strip=True) if preco_div else "N/A"

        header = content.find("div", class_="header")
        link_tag = header.find("a") if header else None
        link = f"https://seminovos.com.br{link_tag['href']}" if link_tag and link_tag.has_attr("href") else "N/A"

        # ❌ Pular carro duplicado
        if link in links_existentes:
            print(f"⏩ Carro já existe no JSON: {link}")
            continue

        titulo = header.find("div", class_="title").get_text(strip=True) if header else "N/A"
        descricao = header.find("div", class_="description").get_text(strip=True) if header else "N/A"

        anunciante_div = header.find("div", class_="my-md-2") if header else None
        anunciante = anunciante_div.get_text(strip=True) if anunciante_div else "N/A"

        img_tag = carro.find("img")
        imagem = img_tag["src"] if img_tag and img_tag.has_attr("src") else "N/A"

        carro_data = {
            "titulo": titulo,
            "descricao": descricao,
            "preco": preco,
            "anunciante": anunciante,
            "link": link,
            "imagem": imagem
        }

        # 🔁 Extrai os detalhes adicionais de cada carro:
        if link != "N/A":
            detalhes = extrair_detalhes_carro(driver, link)
            carro_data["detalhes"] = detalhes
        else:
            carro_data["detalhes"] = {}

        resultados.append(carro_data)
        links_existentes.add(link)

    driver.quit()

    os.makedirs("data", exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Dados de {len(resultados)} carros salvos em '{json_path}'")

if __name__ == "__main__":
    main()
