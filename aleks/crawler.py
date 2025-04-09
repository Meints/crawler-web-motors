import os
import time
import random
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm
import logging
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urljoin
import cloudscraper
import backoff
import re

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)

class OlxCrawler:
    def __init__(self):
        self.estados = {
            'ac': 'Acre',
            'al': 'Alagoas',
            'ap': 'Amapá',
            'am': 'Amazonas',
            'ba': 'Bahia',
            'ce': 'Ceará',
            'df': 'Distrito Federal',
            'es': 'Espírito Santo',
            'go': 'Goiás',
            'ma': 'Maranhão',
            'mt': 'Mato Grosso',
            'ms': 'Mato Grosso do Sul',
            'mg': 'Minas Gerais',
            'pa': 'Pará',
            'pb': 'Paraíba',
            'pr': 'Paraná',
            'pe': 'Pernambuco',
            'pi': 'Piauí',
            'rj': 'Rio de Janeiro',
            'rn': 'Rio Grande do Norte',
            'rs': 'Rio Grande do Sul',
            'ro': 'Rondônia',
            'rr': 'Roraima',
            'sc': 'Santa Catarina',
            'sp': 'São Paulo',
            'se': 'Sergipe',
            'to': 'Tocantins'
        }
        self.base_url_template = "https://www.olx.com.br/autos-e-pecas/carros-vans-e-utilitarios/estado-{estado}"
        self.current_estado = None
        
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, "data")
        self.html_dir = os.path.join(self.data_dir, "html")
        self.json_file = os.path.join(self.data_dir, "anuncios.json")
        
        self.processed_ads = set()  
        self.collected_data = []  
        
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10
        )
        
        self.cookies = {
            'onboarding_olx': 'true',
            'language': 'pt-BR',
            'hasSeenLoginModal': 'true',
        }
        
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        if not os.path.exists(self.html_dir):
            os.makedirs(self.html_dir)
        
        self.load_data()
    
    def load_data(self):
        processed_file = os.path.join(self.data_dir, "processed_ads.json")
        if os.path.exists(processed_file):
            try:
                with open(processed_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_ads = set(data.get("processed_ids", []))
                logging.info(f"Carregados {len(self.processed_ads)} anúncios processados anteriormente.")
            except Exception as e:
                logging.error(f"Erro ao carregar anúncios processados: {e}")
                self.processed_ads = set()
        
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    self.collected_data = json.load(f)
                logging.info(f"Carregados {len(self.collected_data)} anúncios do arquivo JSON.")
            except Exception as e:
                logging.error(f"Erro ao carregar dados dos anúncios: {e}")
                self.collected_data = []
    
    def save_data(self):
        processed_file = os.path.join(self.data_dir, "processed_ads.json")
        try:
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump({"processed_ids": list(self.processed_ads)}, f)
            logging.info(f"Salvos {len(self.processed_ads)} IDs de anúncios processados.")
        except Exception as e:
            logging.error(f"Erro ao salvar anúncios processados: {e}")
        
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.collected_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Salvos {len(self.collected_data)} anúncios no arquivo JSON.")
        except Exception as e:
            logging.error(f"Erro ao salvar dados dos anúncios: {e}")
    
    def get_headers(self):
        chrome_version = f"{random.randint(90, 110)}.0.{random.randint(1000, 5000)}.{random.randint(10, 200)}"
        
        return {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': f'"Google Chrome";v="{chrome_version.split(".")[0]}", "Chromium";v="{chrome_version.split(".")[0]}"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'Referer': 'https://www.google.com/'
        }
    
    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, Exception),
        max_tries=5,
        max_time=300
    )
    def make_request(self, url):
        wait_time = random.uniform(0.2, 2)
        logging.info(f"Aguardando {wait_time:.2f}s antes da requisição...")
        time.sleep(wait_time)
        
        headers = self.get_headers()
        
        try:
            if 'olx.com.br' not in self.session.cookies.get_dict():
                logging.info("Inicializando sessão com página inicial...")
                self.session.get('https://www.olx.com.br/', headers=headers, timeout=30)
                time.sleep(random.uniform(2, 5))
                
            if random.random() > 0.5:
                category_url = 'https://www.olx.com.br/autos-e-pecas'
                logging.info(f"Acessando categoria intermediária: {category_url}")
                self.session.get(category_url, headers=headers, timeout=30)
                time.sleep(random.uniform(3, 7))
            
            logging.info(f"Acessando URL: {url}")
            response = self.session.get(
                url, 
                headers=headers, 
                cookies=self.cookies,
                timeout=45
            )
            
            if response.status_code == 200:
                self.cookies.update(response.cookies.get_dict())
                
                if 'Access Denied' in response.text or 'Forbidden' in response.text:
                    logging.warning("Recebido bloqueio disfarçado como página 200")
                    raise Exception("Bloqueio de acesso detectado")
                
                if 'carros-vans-e-utilitarios' in url and '?' in url:
                    soup = BeautifulSoup(response.text, 'lxml')
                    expected_selectors = [
                        'section[data-ds-component="DS-AdCard"]',
                        'div[data-ds-component="DS-AdCard"]',
                        'div[data-testid="ad-card"]'
                    ]
                    
                    has_ads = any(len(soup.select(selector)) > 0 for selector in expected_selectors)
                    
                    if not has_ads:
                        logging.warning("Página não contém cards de anúncios esperados")
                
                return response
            else:
                logging.warning(f"Resposta não-200: {response.status_code} para URL: {url}")
                if response.status_code == 403:
                    logging.error("Bloqueio detectado! Esperando tempo maior...")
                    time.sleep(random.uniform(60, 180))
                return None
                
        except Exception as e:
            logging.error(f"Erro na requisição para {url}: {e}")
            if "Bloqueio de acesso detectado" in str(e):
                time.sleep(random.uniform(120, 300))
            return None
    
    def extract_ad_id(self, ad_url):
        if not ad_url:
            return None
        
        try:
            path_parts = urlparse(ad_url).path.split('/')
            for part in path_parts:
                if part.startswith('id-'):
                    return part
                
                # Checar por partes numéricas que sejam IDs
                if part and part[0].isdigit():
                    # Extrair apenas a parte numérica no início
                    numeric_part = ''
                    for char in part:
                        if char.isdigit():
                            numeric_part += char
                        else:
                            break
                    
                    if numeric_part and len(numeric_part) > 5:
                        return numeric_part
            
            # Se falhar, usar hash da URL
            return hashlib.md5(ad_url.encode()).hexdigest()
            
        except Exception as e:
            logging.error(f"Erro ao extrair ID do anúncio {ad_url}: {e}")
            return hashlib.md5(ad_url.encode()).hexdigest()
    
    def save_ad_html(self, ad_id, html_content):
        if not ad_id:
            return False
        
        filename = os.path.join(self.html_dir, f"ad_{ad_id}.html")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return True
        except Exception as e:
            logging.error(f"Erro ao salvar HTML do anúncio {ad_id}: {e}")
            return False
    
    def extract_ad_data(self, ad_url, html_content):
        ad_id = self.extract_ad_id(ad_url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        ad_data = {
            "id": ad_id,
            "url": ad_url,
            "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "estado": self.estados.get(self.current_estado, self.current_estado)
        }
        
        try:
            logging.info(f"Iniciando extração de dados para anúncio {ad_id}")
            
            # Nova estrutura do site da OLX - extração do título/modelo
            title_element = soup.select_one('h1.olx-text--title-large, h1.olx-text--title-xlarge, h1.olx-ad-title, span[data-testid="ad-title"]')
            if title_element:
                modelo = title_element.text.strip()
                ad_data['modelo'] = modelo
                logging.info(f"Modelo encontrado no título: {modelo}")
            
            # Extração dos detalhes do anúncio da seção 'details'
            details_section = soup.select_one('div#details')
            detail_containers = []
            
            if details_section:
                logging.info("Seção de detalhes encontrada pelo ID")
                detail_containers = details_section.select('div.ad__sc-2h9gkk-0.dLQbjb')
            
            if not detail_containers:
                # Tentar seletores alternativos
                logging.info("Tentando seletores alternativos para os detalhes")
                detail_elements = soup.select('div[data-ds-component="DS-AdDetails"] div[data-testid="ad-properties-item"]')
                if not detail_elements:
                    detail_elements = soup.select('div[data-testid="ad-properties"] div[data-testid="ad-properties-item"], div[data-testid="properties-card"] div[data-testid="ad-properties-item"]')
            else:
                logging.info(f"Encontrados {len(detail_containers)} containers de detalhes do anúncio")
                # Processar os containers de detalhes
                for container in detail_containers:
                    try:
                        # Pegar o label para saber qual detalhe está sendo extraído
                        label_element = container.select_one('span[data-variant="overline"]')
                        if not label_element:
                            continue
                            
                        label_text = label_element.text.strip().lower()
                        logging.info(f"Processando detalhe: {label_text}")
                        
                        # Pegar o valor do detalhe (pode ser em um 'a' ou 'span')
                        value_element = container.select_one('a.olx-link, span.ekhFnR, span:not([data-variant])')
                        if not value_element:
                            continue
                            
                        value_text = value_element.text.strip()
                        
                        # Mapear os diferentes tipos de detalhes
                        if 'marca' in label_text:
                            ad_data['marca'] = value_text
                            logging.info(f"Marca encontrada: {value_text}")
                        elif 'modelo' in label_text:
                            if not ad_data.get('modelo'):
                                ad_data['modelo'] = value_text
                                logging.info(f"Modelo encontrado nos detalhes: {value_text}")
                        elif 'tipo de veículo' in label_text:
                            ad_data['tipo_veiculo'] = value_text
                            logging.info(f"Tipo de veículo: {value_text}")
                        elif 'ano' in label_text:
                            ad_data['ano'] = value_text
                            logging.info(f"Ano: {value_text}")
                        elif 'quilometragem' in label_text:
                            ad_data['quilometragem'] = value_text
                            logging.info(f"Quilometragem: {value_text}")
                        elif 'potência do motor' in label_text:
                            ad_data['potencia'] = value_text
                            logging.info(f"Potência do motor: {value_text}")
                        elif 'combustível' in label_text:
                            ad_data['combustivel'] = value_text
                            logging.info(f"Combustível: {value_text}")
                        elif 'câmbio' in label_text:
                            ad_data['cambio'] = value_text
                            logging.info(f"Câmbio: {value_text}")
                        elif 'direção' in label_text or 'tipo de direção' in label_text:
                            ad_data['direcao'] = value_text
                            logging.info(f"Direção: {value_text}")
                        elif 'cor' in label_text:
                            ad_data['cor'] = value_text
                            logging.info(f"Cor: {value_text}")
                        elif 'portas' in label_text:
                            ad_data['portas'] = value_text
                            logging.info(f"Portas: {value_text}")
                        elif 'final de placa' in label_text:
                            ad_data['final_placa'] = value_text
                            logging.info(f"Final de placa: {value_text}")
                        elif 'gnv' in label_text:
                            ad_data['gnv'] = value_text
                            logging.info(f"Possui GNV: {value_text}")
                        elif 'categoria' in label_text:
                            ad_data['categoria'] = value_text
                            logging.info(f"Categoria: {value_text}")
                    except Exception as detail_error:
                        logging.error(f"Erro ao extrair detalhe: {detail_error}")
                        
            # Se não encontrou detalhes na seção específica, tentar métodos alternativos
            if not any(key in ad_data for key in ['marca', 'combustivel', 'ano', 'quilometragem']):
                logging.warning("Detalhes não encontrados na seção principal, tentando métodos alternativos")
                
                # Tentar encontrar detalhes em outros formatos
                if detail_elements:
                    logging.info(f"Encontrados {len(detail_elements)} elementos de detalhes alternativos")
                    for detail in detail_elements:
                        try:
                            label = detail.select_one('span.olx-text--caption')
                            value = detail.select_one('span.olx-text--body-large, span.olx-text--body, span:not(.olx-text--caption), a')
                            
                            if label and value:
                                label_text = label.text.strip().lower()
                                value_text = value.text.strip()
                                
                                if 'marca' in label_text:
                                    ad_data['marca'] = value_text
                                elif 'modelo' in label_text and not ad_data.get('modelo'):
                                    ad_data['modelo'] = value_text
                                # Adicionar outros mapeamentos conforme necessário
                        except Exception as e:
                            logging.error(f"Erro ao extrair detalhe alternativo: {e}")
                
                # Tentar encontrar marca/modelo em outras partes da página
                breadcrumb = soup.select('ol[data-testid="breadcrumb"] li a')
                if breadcrumb and len(breadcrumb) >= 3:
                    possible_brand = breadcrumb[2].text.strip()
                    ad_data['marca'] = possible_brand
                    logging.info(f"Marca extraída do breadcrumb: {possible_brand}")

            # Se ainda não tiver marca, tentar extrair do título
            if not ad_data.get('marca') and ad_data.get('modelo'):
                primeira_palavra = ad_data['modelo'].split()[0]
                marcas_comuns = ['honda', 'toyota', 'volkswagen', 'vw', 'fiat', 'chevrolet', 'ford', 'hyundai', 'nissan', 'renault']
                if primeira_palavra.lower() in marcas_comuns:
                    ad_data['marca'] = primeira_palavra
                    logging.info(f"Marca extraída do título: {primeira_palavra}")
                else:
                    ad_data['marca'] = "Marca não encontrada"
            
            # Nova estrutura para extrair preço
            try:
                logging.info("Extraindo preço do anúncio...")
                
                # Primeiro tentar pela div específica do preço
                price_box = soup.select_one('div#price-box-container')
                if price_box:
                    logging.info("Encontrado container de preço específico")
                    # Procurar dentro do container específico do preço
                    price_span = price_box.select_one('span.olx-text--title-large, span[class*="title-large"]')
                    if price_span and 'R$' in price_span.text:
                        preco_valor = price_span.text.strip()
                        logging.info(f"Preço encontrado no price-box-container: {preco_valor}")
                        ad_data['preco'] = preco_valor
                    else:
                        # Se não encontrar o span específico, buscar qualquer texto que tenha R$ no container
                        price_text = re.search(r'R\$\s*[\d.,]+', price_box.text)
                        if price_text:
                            preco_valor = price_text.group(0).strip()
                            logging.info(f"Preço encontrado com regex no price-box-container: {preco_valor}")
                            ad_data['preco'] = preco_valor
                else:
                    # Tentar seletores alternativos se não encontrar o container específico
                    price_element = soup.select_one('div[data-testid="ad-price-wrapper"] span, span[data-ds-component="DS-Text"][class*="olx-text--title"]')
                    if price_element and 'R$' in price_element.text:
                        preco_valor = price_element.text.strip()
                        logging.info(f"Preço encontrado no elemento alternativo: {preco_valor}")
                        ad_data['preco'] = preco_valor
                    else:
                        # Último recurso: tentar encontrar qualquer elemento com R$
                        price_regex = re.compile(r'R\$\s*[\d.,]+')
                        for element in soup.find_all(['span', 'div', 'p']):
                            if element.text and price_regex.search(element.text):
                                preco_valor = price_regex.search(element.text).group(0).strip()
                                logging.info(f"Preço encontrado com regex: {preco_valor}")
                                ad_data['preco'] = preco_valor
                                break
                        else:
                            logging.warning("Preço não encontrado no anúncio")
                            ad_data['preco'] = "Preço não encontrado"
            except Exception as e:
                logging.error(f"Erro ao extrair preço: {e}")
                ad_data['preco'] = "Erro na extração"
            if ad_data['modelo'] == "Modelo não encontrado":
                debug_file = os.path.join(self.data_dir, f"debug_extraction_{ad_id}.html")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logging.warning(f"Falha na extração completa de dados para anúncio {ad_id}. HTML salvo para debug.")
            
            logging.info(f"Dados extraídos com sucesso para anúncio {ad_id}: {ad_data['modelo']} - {ad_data.get('preco', 'N/A')}")
            return ad_data
            
        except Exception as e:
            logging.error(f"Erro ao extrair dados do anúncio {ad_id}: {e}")
            debug_file = os.path.join(self.data_dir, f"debug_error_{ad_id}.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return ad_data
    
    def process_ad(self, ad_url):
        ad_id = self.extract_ad_id(ad_url)
        
        if not ad_id:
            logging.warning(f"Não foi possível extrair ID para URL: {ad_url}")
            return False
        
        if ad_id in self.processed_ads:
            logging.debug(f"Anúncio {ad_id} já processado anteriormente.")
            return False
        
        response = self.make_request(ad_url)
        if not response:
            return False
        
        html_saved = self.save_ad_html(ad_id, response.text)
        
        ad_data = self.extract_ad_data(ad_url, response.text)
        
        if html_saved:
            self.processed_ads.add(ad_id)
            self.collected_data.append(ad_data)
            logging.info(f"Anúncio {ad_id} processado e salvo com sucesso.")
            return True
        
        return False
    
    def extract_ad_links(self, html_content):
        soup = BeautifulSoup(html_content, 'lxml')
        ad_links = []
        logging.info("Extraindo links de anúncios da página...")
    
        # Nova estrutura do site da OLX - 2023/2024
        primary_selectors = [
            'a[data-testid="adcard-link"]',  # Novo seletor principal da OLX (2024)
            'a.AdCard_link__4c7W6',  # Seletor de classe do card de anúncio
            'a[href*="/autos-e-pecas/carros-vans-e-utilitarios/"][href*="-"]', # Links de anúncios específicos
            'a[data-testid="ad-card-link"]',  # Outro seletor possível
            'div[data-testid="listing-card"] a', # Seletor alternativo
            'a[data-ds-component="DS-Link"][href*="/item"]', # Formato de link
            'div[data-testid="ad-card"] a',  # Outro seletor
            'section[data-ds-component="DS-AdCard"] a',  # Seletor antigo
            'div[data-ds-component="DS-AdCard"] a'  # Seletor antigo
        ]
        
        for selector in primary_selectors:
            ad_elements = soup.select(selector)
            if ad_elements:
                logging.info(f"Encontrados {len(ad_elements)} links usando seletor: {selector}")
                for element in ad_elements:
                    href = element.get('href')
                    if href:
                        # Usamos urljoin com URL base da OLX em vez de self.base_url
                        full_url = urljoin("https://www.olx.com.br", href)
                        ad_links.append(full_url)
                if ad_links:  # Se encontrou links com este seletor, podemos prosseguir
                    break
        
        if not ad_links:
            logging.info("Usando seletores alternativos para encontrar links...")
            fallback_selectors = [
                'a[href*="/item/"]',  # Links de item genérico
                'a[data-lurker-detail="list_id"]',  # Seletor antigo
                'a[href*="olx.com.br/autos-e-pecas/carros"]',  # Links diretos para carros
                'a.olx-ad-card__link-wrapper',  # Classe específica de cards
                'a[href*="carros-vans-e-utilitarios/"]'  # Padrão de URL para carros
            ]
            
            for selector in fallback_selectors:
                elements = soup.select(selector)
                if elements:
                    logging.info(f"Encontrados {len(elements)} links usando seletor alternativo: {selector}")
                    for element in elements:
                        href = element.get('href')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            ad_links.append(full_url)
                    if ad_links:  # Se encontrou links com este seletor, podemos prosseguir
                        break
        
        if not ad_links:
            logging.info("Último recurso: buscando todos os links e filtrando por padrões relevantes...")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                # Ampliando os padrões de URL para capturar mais anúncios
                if (
                    '/item/' in href or 
                    ('/autos-e-pecas/carros-vans-e-utilitarios/' in href and not href.endswith('carros-vans-e-utilitarios/')) or
                    ('/anuncio/' in href) or
                    ('/d/' in href and 'carros' in href)
                ):
                    full_url = urljoin(self.base_url, href)
                    ad_links.append(full_url)
        
        unique_links = []
        for url in ad_links:
            # Ampliando os critérios de validação
            is_valid = (
                '/item/' in url or 
                '/anuncio/' in url or
                ('/d/' in url and 'carros' in url) or
                ('/autos-e-pecas/carros-vans-e-utilitarios/' in url and not url.endswith('carros-vans-e-utilitarios/'))
            )
            if is_valid and url not in unique_links:
                unique_links.append(url)
        
        logging.info(f"Total de {len(unique_links)} links únicos de anúncios extraídos")
        
        if not unique_links:
            logging.warning("Nenhum link de anúncio encontrado. Salvando HTML para debug")
            with open("debug_no_links_found.html", "w", encoding="utf-8") as f:
                f.write(html_content)
                
            with open("debug_page_structure.txt", "w", encoding="utf-8") as f:
                possible_containers = soup.select('section, div[data-ds], div[data-testid], li, a[href*="/item/"], a[href*="olx.com.br/"]')
                f.write(f"Possíveis contêineres: {len(possible_containers)}\n\n")
                
                for i, container in enumerate(possible_containers[:30]):
                    f.write(f"Container {i+1}:\n")
                    f.write(f"Tag: {container.name}\n")
                    f.write(f"Classes: {container.get('class')}\n")
                    f.write(f"Data attrs: {[attr for attr in container.attrs if attr.startswith('data-')]}\n")
                    if container.name == 'a':
                        f.write(f"Href: {container.get('href')}\n")
                    f.write(f"Links: {len(container.select('a'))}\n\n")
        
        return unique_links
    
    def extract_next_page(self, html_content, current_page):
        soup = BeautifulSoup(html_content, 'lxml')
        
        next_button = soup.find('a', text=lambda t: t and ('Próxima' in t or 'Próximo' in t or 'próxima' in t))
        if next_button and next_button.get('href'):
            return urljoin(self.base_url, next_button['href'])
        
        pagination_links = soup.select('a[data-lurker-detail="pagination"]')
        for link in pagination_links:
            try:
                page_num = int(link.text.strip())
                if page_num == current_page + 1:
                    return urljoin(self.base_url, link['href'])
            except (ValueError, AttributeError):
                continue
        
        next_page = current_page + 1
        return f"{self.base_url}?o={next_page}"
    
    def crawl_estado(self, estado, max_pages=100):
        """
        Executa o crawler para um estado específico
        """
        self.current_estado = estado
        base_url = self.base_url_template.format(estado=estado)
        current_page = 1
        current_url = base_url
        total_ads_processed = 0
        consecutive_errors = 0
        
        logging.info(f"Iniciando crawler para o estado: {self.estados.get(estado, estado)}")
        
        try:
            while current_page <= max_pages:
                logging.info(f"Processando página {current_page} de {self.estados.get(estado, estado)}: {current_url}")
                
                response = self.make_request(current_url)
                if not response:
                    consecutive_errors += 1
                    logging.error(f"Não foi possível acessar a página {current_page}")
                    
                    if consecutive_errors >= 3:
                        logging.error("Muitos erros consecutivos. Pausando por um período maior...")
                        time.sleep(random.uniform(300, 600))  # 5-10 minutos
                        
                        logging.info("Reiniciando sessão...")
                        self.session = cloudscraper.create_scraper(
                            browser={
                                'browser': 'chrome',
                                'platform': 'windows',
                                'desktop': True
                            }
                        )
                        
                        # Em caso de muitos erros, tentar URL alternativa
                        if current_page > 1:
                            current_url = f"{base_url}?o={current_page}"
                        
                        consecutive_errors = 0
                        continue
                    else:
                        time.sleep(random.uniform(30, 60))  # Espera 30-60 segundos antes de tentar novamente
                        continue
                
                consecutive_errors = 0  # Reinicia contador de erros após sucesso
                
                ad_links = self.extract_ad_links(response.text)
                logging.info(f"Encontrados {len(ad_links)} anúncios na página {current_page} de {self.estados.get(estado, estado)}")
                
                if not ad_links:
                    logging.warning(f"Nenhum anúncio encontrado na página {current_page}. Salvando para análise.")
                    
                    with open(f"debug_page_{estado}_{current_page}.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    
                    current_page += 1
                    current_url = f"{base_url}?o={current_page}"
                    time.sleep(random.uniform(60, 120))  # Espera maior antes de tentar a próxima
                    continue
                
                for ad_url in tqdm(ad_links, desc=f"{self.estados.get(estado, estado)} - Página {current_page}"):
                    success = self.process_ad(ad_url)
                    if success:
                        total_ads_processed += 1
                    
                    if total_ads_processed % 10 == 0:
                        self.save_data()
                    
                    time.sleep(random.uniform(1, 3))
                
                next_url = self.extract_next_page(response.text, current_page)
                if not next_url or next_url == current_url:
                    logging.info(f"Nenhuma próxima página encontrada para {self.estados.get(estado, estado)}. Finalizando.")
                    break
                
                current_url = next_url
                current_page += 1
                
                wait_time = random.uniform(15, 30)
                logging.info(f"Aguardando {wait_time:.2f}s antes de acessar a próxima página...")
                time.sleep(wait_time)
                
                self.save_data()
                
        except KeyboardInterrupt:
            logging.info("Interrompido pelo usuário.")
            return total_ads_processed
        except Exception as e:
            logging.error(f"Erro durante o crawling do estado {self.estados.get(estado, estado)}: {e}", exc_info=True)
            return total_ads_processed
        
        logging.info(f"Crawling do estado {self.estados.get(estado, estado)} finalizado. Total de anúncios processados: {total_ads_processed}")
        return total_ads_processed

    def crawl(self, estados=None, max_pages=100):
        """
        Executa o crawler para uma lista de estados
        estados: lista de siglas de estados (ex: ['sp', 'rj'])
        max_pages: número máximo de páginas por estado
        """
        if estados is None:
            estados = ['sp']  # Por padrão, apenas São Paulo
        
        total_geral = 0
        
        try:
            for estado in estados:
                if estado.lower() in self.estados:
                    ads_processados = self.crawl_estado(estado.lower(), max_pages)
                    total_geral += ads_processados
                    
                    # Pausa entre estados para reduzir a chance de detecção
                    wait_time = random.uniform(60, 180)
                    logging.info(f"Concluído estado {self.estados.get(estado.lower())}. Aguardando {wait_time:.2f}s antes do próximo estado...")
                    time.sleep(wait_time)
                else:
                    logging.warning(f"Estado {estado} não reconhecido. Ignorando.")
        
        except KeyboardInterrupt:
            logging.info("Interrompido pelo usuário.")
        except Exception as e:
            logging.error(f"Erro durante o crawling: {e}", exc_info=True)
        finally:
            self.save_data()
            logging.info(f"Crawling de todos estados finalizado. Total de anúncios processados: {total_geral}")

# Para executar o crawler
if __name__ == "__main__":
    try:
        crawler = OlxCrawler()
        estados = ['sp', 'rj', 'mg', 'ba', 'sc']
        crawler.crawl(estados=estados, max_pages=100)
    except Exception as e:
        logging.error(f"Erro ao executar crawler: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Erro ao executar crawler: {e}", exc_info=True)