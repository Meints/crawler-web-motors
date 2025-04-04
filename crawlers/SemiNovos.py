import time
import json
import undetected_chromedriver as uc
from bs4 import BeautifulSoup

def scroll_until_end(driver, pause_time=5, max_attempts=10):
    """
    Rola a página até que não haja mais alterações na altura ou atinja o número máximo de tentativas.
    """
    attempts = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while attempts < max_attempts:
        # Rola até o final da página
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause_time)  # Aguarda o carregamento de novos elementos
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            print("Chegou ao final da página.")
            break
        last_height = new_height
        attempts += 1
        print(f"Tentativa {attempts}: altura atual = {last_height}")

def extrair_detalhes_carro(driver, url):
    """
    Acessa a página do carro e extrai os detalhes da seção de ícones.
    """
    print(f"Acessando detalhes: {url}")
    driver.get(url)
    time.sleep(5)  # Aguarda o carregamento da página
    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")
    
    detalhes_div = soup.find("div", class_="part-items-detalhes-icones")
    detalhes = {}
    
    if detalhes_div:
        items = detalhes_div.find_all("div", class_="item")
        for item in items:
            # Pega o nome do campo (ex: "Quilometragem")
            campo_div = item.find("div", class_="campo")
            # Pega o valor correspondente (ex: "107.500 km")
            valor_span = item.find("span", class_="valor")
            if campo_div and valor_span:
                campo = campo_div.get_text(strip=True).lower()
                valor = valor_span.get_text(strip=True)
                detalhes[campo] = valor
    else:
        print("Seção de detalhes não encontrada na página de detalhes.")
    
    return detalhes

def main():
    options = uc.ChromeOptions()
    options.headless = False  # Permite visualização e resolução manual de CAPTCHA, se necessário
    driver = uc.Chrome(options=options)

    url = "https://seminovos.com.br/carros"
    driver.get(url)
    time.sleep(5)  # Aguarda o carregamento completo da página inicial

    # Rola até o final da página para carregar mais carros
    scroll_until_end(driver, pause_time=5, max_attempts=10)

    html = driver.page_source
    soup = BeautifulSoup(html, "html.parser")

    # Verifica se a div que contém os anúncios foi encontrada
    anuncios_div = soup.find("div", class_="anuncios")
    if not anuncios_div:
        print("Não foi possível encontrar a div 'anuncios'. Verifique se o conteúdo foi carregado ou se os seletores estão atualizados.")
        driver.quit()
        return

    # Seleciona os elementos de cada anúncio
    carros = anuncios_div.find_all("div", class_="anuncio-thumb-new")
    resultados = []

    # Extrai dados básicos de cada anúncio
    for idx, carro in enumerate(carros):
        # Limite opcional: caso deseje extrair somente os 30 primeiros itens
        if idx >= 30:
            break

        content = carro.find("div", class_="content border-plano-nitro")
        if not content:
            continue

        # Preço
        preco_div = content.find("div", class_="value")
        preco = preco_div.get_text(strip=True) if preco_div else "N/A"

        # Link, título e descrição
        header = content.find("div", class_="header")
        link_tag = header.find("a") if header else None
        link = f"https://seminovos.com.br{link_tag['href']}" if link_tag and link_tag.has_attr("href") else "N/A"
        titulo = header.find("div", class_="title").get_text(strip=True) if header else "N/A"
        descricao = header.find("div", class_="description").get_text(strip=True) if header else "N/A"

        # Anunciante
        anunciante_div = header.find("div", class_="my-md-2") if header else None
        anunciante = anunciante_div.get_text(strip=True) if anunciante_div else "N/A"

        # Imagem
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
        resultados.append(carro_data)

    # Para cada carro, acessa a página de detalhes e extrai informações adicionais
    for carro in resultados:
        link = carro.get("link")
        if link and link != "N/A":
            detalhes = extrair_detalhes_carro(driver, link)
            carro["detalhes"] = detalhes
        else:
            carro["detalhes"] = {}

    driver.quit()

    # Salva os resultados com os detalhes adicionais em um arquivo JSON
    with open("carros_seminovos_com_detalhes.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    print(f"✅ Dados de {len(resultados)} carros salvos em 'carros_seminovos_com_detalhes.json'")

if __name__ == "__main__":
    main()
