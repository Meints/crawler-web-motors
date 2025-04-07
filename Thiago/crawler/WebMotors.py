import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import random

# Variável global para contar as páginas coletadas (escala)
pages_collected = 0

# Exceção personalizada para acesso negado
class AccessDeniedException(Exception):
    pass

def get_html(url, headless=True, retries=3, wait_range=(8, 12)):
    """
    Obtém o HTML da página especificada, implementando um mecanismo de retry
    em caso de "Access Denied" ou outros erros.
    Incrementa o contador global de páginas coletadas para medir a escala.
    """
    global pages_collected
    attempt = 0
    while attempt < retries:
        options = uc.ChromeOptions()
        options.headless = headless
        driver = uc.Chrome(options=options)
        try:
            driver.get(url)
            # Aguarda um tempo aleatório para simular comportamento humano
            time.sleep(random.uniform(*wait_range))
            html = driver.page_source
            pages_collected += 1
            # Verifica se a página indica acesso negado
            if "Access Denied" in html or "acesso negado" in html:
                raise AccessDeniedException("Access Denied ao acessar: " + url)
            return html
        except AccessDeniedException as ade:
            print(f"Tentativa {attempt+1} de {retries} falhou com Access Denied para {url}. Retentando...")
            attempt += 1
            time.sleep(random.uniform(5, 10))
        except Exception as e:
            print(f"Tentativa {attempt+1} de {retries} falhou com erro: {str(e)}. Retentando...")
            attempt += 1
            time.sleep(random.uniform(5, 10))
        finally:
            driver.quit()
    raise AccessDeniedException("Todas as tentativas falharam para a URL: " + url)

def coletar_marcas():
    """
    Coleta as marcas de carros na página principal da tabela FIPE da WebMotors.
    - Carrega a página principal.
    - Clica no botão "Ver todas as marcas" para exibir a lista completa.
    - Extrai os dados de cada marca (nome, URL e logo).
    Retorna uma lista de dicionários com os dados de cada marca.
    """
    options = uc.ChromeOptions()
    options.headless = False  # Permite visualização e resolução manual de CAPTCHA, se necessário
    driver = uc.Chrome(options=options)
    
    url = "https://www.webmotors.com.br/tabela-fipe/carros"
    driver.get(url)
    
    print("Aguarde e resolva o CAPTCHA, se necessário...")
    time.sleep(10)  # Tempo para resolução de CAPTCHA, se aparecer
    
    # Tenta clicar no botão "Ver todas as marcas"
    try:
        button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.button"))
        )
        button.click()
        print("Botão 'Ver todas as marcas' clicado.")
        time.sleep(5)  # Aguarda o carregamento da lista completa
    except Exception as e:
        print("Botão 'Ver todas as marcas' não encontrado ou não foi possível clicar:", e)
    
    html = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(html, 'html.parser')
    marcas = soup.find_all("a", class_="brand-logo")
    
    if not marcas:
        print("Nenhuma marca encontrada. Verifique os seletores.")
        return []
    
    dados_marcas = []
    for marca in marcas:
        nome_marca = marca.find_next("h3")
        logo = marca.find("img")
        dados_marcas.append({
            "marca": nome_marca.get_text(strip=True) if nome_marca else "N/D",
            "url": marca.get("href") if marca.has_attr("href") else "N/D",
            "logo": logo.get("src") if logo and logo.has_attr("src") else "N/D",
        })
    
    return dados_marcas

def coletar_anos_e_precos(url):
    """
    Coleta os anos disponíveis e os preços para um determinado modelo.
    Na página do modelo, as informações de ano e preço já aparecem juntas.
    Retorna uma lista de dicionários com o ano, a URL associada e o preço.
    """
    html = get_html(url, headless=True, retries=3)
    soup = BeautifulSoup(html, 'html.parser')
    
    cards_div = soup.find("div", class_="cards-list")
    if not cards_div:
        print(f"Lista de anos não encontrada para URL: {url}")
        return []
    
    card_list = cards_div.find_all("a", class_="card--carros")
    
    anos = []
    for card in card_list:
        ano_tag = card.find("h3", class_="card-title")
        preco_tag = card.find("h3", class_="card-subtitle")
        ano_text = ano_tag.get_text(strip=True) if ano_tag else "Ano não disponível"
        preco_text = preco_tag.get_text(strip=True) if preco_tag else "Preço não disponível"
        href = card.get("href", "N/D")
        
        anos.append({
            "ano": ano_text,
            "url": href,
            "preco": preco_text,
        })
    
    return anos

def coletar_carros_por_marca(url):
    """
    Coleta os modelos de carros para uma marca específica.
    Na página da marca, extrai os modelos (nome e URL) e, para cada modelo,
    coleta os anos disponíveis e os preços correspondentes.
    Retorna uma lista de dicionários com os dados do modelo e suas informações.
    """
    html = get_html(url, headless=True, retries=3)
    soup = BeautifulSoup(html, 'html.parser')
    modelos = soup.find_all("li", class_="brand-items__item")
    
    carros = []
    for modelo in modelos:
        nome_tag = modelo.find("h3", class_="brand-items__label")
        link = modelo.find("a")
        
        carro = {
            "modelo": nome_tag.get_text(strip=True) if nome_tag else "N/D",
            "url": link["href"] if link and link.has_attr("href") else "N/D",
        }
        
        if carro["url"] != "N/D":
            print(f"  Coletando anos e preços para o modelo: {carro['modelo']}")
            carro["anos_e_precos"] = coletar_anos_e_precos(carro["url"])
            time.sleep(random.uniform(3, 6))
        else:
            carro["anos_e_precos"] = []
        
        carros.append(carro)
    
    return carros

def coletar_dados_completos():
    """
    Coordena a coleta completa dos dados da tabela FIPE na WebMotors:
    1. Coleta todas as marcas (clicando em "Ver todas as marcas").
    2. Para cada marca, coleta os modelos disponíveis.
    3. Para cada modelo, coleta os anos disponíveis e os preços.
    Retorna um dicionário com os metadados de escala e os dados coletados.
    """
    marcas = coletar_marcas()
    if not marcas:
        return []
    
    dados_completos = []
    for marca in marcas:
        print(f"Coletando modelos para a marca: {marca['marca']}")
        modelos = coletar_carros_por_marca(marca["url"])
        marca["modelos"] = modelos
        dados_completos.append(marca)
        time.sleep(random.uniform(3, 6))
    
    return dados_completos

if __name__ == "__main__":
    try:
        dados = coletar_dados_completos()
        resultado_final = {
            "meta": {
                "paginas_coletadas": pages_collected
            },
            "dados": dados
        }
        with open("dados_webmotors.json", "w", encoding="utf-8") as f:
            json.dump(resultado_final, f, ensure_ascii=False, indent=4)
        print("Dados salvos em dados_webmotors.json")
        print(f"Total de páginas coletadas: {pages_collected}")
    except AccessDeniedException as ade:
        erro = {"error": str(ade)}
        with open("dados_webmotors.json", "w", encoding="utf-8") as f:
            json.dump(erro, f, ensure_ascii=False, indent=4)
        print(json.dumps(erro, indent=4))
