from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json
import time

def coletar_carros_localiza(max_scrolls=500, arquivo_saida="carros_localiza_completo.json"):
    # Configurações do Selenium
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)

    try:
        # URL alvo
        url = "https://seminovos.localiza.com/carros"
        driver.get(url)

        # Esperar o carregamento inicial da página
        time.sleep(5)

        # Tenta clicar no botão "Ver mais carros", se existir
        try:
            ver_mais = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Mostrar mais')]"))
            )
            ver_mais.click()
            print("Botão 'Ver mais carros' clicado.")
            time.sleep(2)
        except Exception as e:
            print("Botão 'Ver mais carros' não encontrado ou erro:", e)

        # Scroll progressivo
        last_height = driver.execute_script("return document.body.scrollHeight")

        for i in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print(f"Scroll completo após {i + 1} interações.")
                break
            last_height = new_height

        # Pega o HTML completo
        html = driver.page_source

    finally:
        # Fecha o navegador em qualquer caso
        driver.quit()

    # Faz o parsing com BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.find_all('div', class_='ng-star-inserted')

    carros = []

    for card in cards:
        try:
            marca_el = card.find('h2', class_='title-car')
            marca = marca_el.text.strip() if marca_el else ""

            modelo_el = card.find('h2', class_='subtitle-car-primary')
            modelo = modelo_el.text.strip() if modelo_el else ""

            km_el = card.find('span', id=lambda x: x and 'odometer-value' in x)
            km = km_el.text.strip() if km_el else ""

            ano_el = card.find('span', id=lambda x: x and 'year-value' in x)
            ano = ano_el.text.strip() if ano_el else ""

            cambio_el = card.find('span', id=lambda x: x and 'transmition-type' in x)
            cambio = cambio_el.text.strip() if cambio_el else ""

            preco_de_el = card.find('span', class_='text-price-of')
            preco_de = preco_de_el.text.strip() if preco_de_el else ""

            preco_el = card.find('span', class_='text-price')
            preco = preco_el.text.strip() if preco_el else ""

            local_el = card.find('span', class_='text-location')
            local = local_el.text.strip() if local_el else ""

            link = card.find('a', class_='container-body-link', href=True)
            link_final = "https://seminovos.localiza.com" + link['href'] if link else ""

            carros.append({
                "marca": marca,
                "modelo": modelo,
                "km": km,
                "ano": ano,
                "cambio": cambio,
                "preco_de": preco_de,
                "preco": preco,
                "local": local,
                "link": link_final
            })
        except Exception as e:
            print(f"Erro ao processar um card: {e}")

    # Exporta para JSON
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        json.dump(carros, f, ensure_ascii=False, indent=4)

    print(f"✅ Captura finalizada com {len(carros)} carros exportados para {arquivo_saida}.")
    return carros
