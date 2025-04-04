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
        # Configurações básicas
        self.base_url = "https://www.olx.com.br/autos-e-pecas/carros-vans-e-utilitarios"
        self.data_dir = "data"
        self.html_dir = os.path.join(self.data_dir, "html")
        self.json_file = os.path.join(self.data_dir, "anuncios.json")
        self.processed_ads = set()  # Conjunto para rastrear anúncios processados
        self.collected_data = []  # Lista para armazenar dados dos anúncios
        
        # Configuração do scraper com bypass de proteções
        self.session = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10
        )
        
        # Cookies iniciais para simular comportamento humano
        self.cookies = {
            'onboarding_olx': 'true',
            'language': 'pt-BR',
            'hasSeenLoginModal': 'true',
        }
        
        # Criar diretórios se não existirem
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
        
        if not os.path.exists(self.html_dir):
            os.makedirs(self.html_dir)
        
        # Carregar anúncios já processados e dados coletados
        self.load_data()
    
    def load_data(self):
        """Carrega dados anteriormente salvos (anúncios processados e dados coletados)."""
        # Carregar IDs de anúncios processados
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
        
        # Carregar dados coletados anteriormente
        if os.path.exists(self.json_file):
            try:
                with open(self.json_file, 'r', encoding='utf-8') as f:
                    self.collected_data = json.load(f)
                logging.info(f"Carregados {len(self.collected_data)} anúncios do arquivo JSON.")
            except Exception as e:
                logging.error(f"Erro ao carregar dados dos anúncios: {e}")
                self.collected_data = []
    
    def save_data(self):
        """Salva os IDs processados e dados coletados."""
        # Salvar IDs processados
        processed_file = os.path.join(self.data_dir, "processed_ads.json")
        try:
            with open(processed_file, 'w', encoding='utf-8') as f:
                json.dump({"processed_ids": list(self.processed_ads)}, f)
            logging.info(f"Salvos {len(self.processed_ads)} IDs de anúncios processados.")
        except Exception as e:
            logging.error(f"Erro ao salvar anúncios processados: {e}")
        
        # Salvar dados coletados em JSON
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.collected_data, f, ensure_ascii=False, indent=2)
            logging.info(f"Salvos {len(self.collected_data)} anúncios no arquivo JSON.")
        except Exception as e:
            logging.error(f"Erro ao salvar dados dos anúncios: {e}")
    
    def get_headers(self):
        """Gera cabeçalhos HTTP realistas para evitar bloqueio."""
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
        """Faz uma requisição HTTP com retry exponencial e simulação de comportamento humano."""
        wait_time = random.uniform(2, 6)
        logging.info(f"Aguardando {wait_time:.2f}s antes da requisição...")
        time.sleep(wait_time)
        
        headers = self.get_headers()
        
        try:
            # Inicializar sessão com página inicial para obter cookies
            if 'olx.com.br' not in self.session.cookies.get_dict():
                logging.info("Inicializando sessão com página inicial...")
                self.session.get('https://www.olx.com.br/', headers=headers, timeout=30)
                time.sleep(random.uniform(2, 5))
                
            # Ocasionalmente navegar por uma categoria intermediária (comportamento humano)
            if random.random() > 0.7:
                category_url = 'https://www.olx.com.br/autos-e-pecas'
                logging.info(f"Acessando categoria intermediária: {category_url}")
                self.session.get(category_url, headers=headers, timeout=30)
                time.sleep(random.uniform(3, 7))
            
            # Fazer a requisição real
            logging.info(f"Acessando URL: {url}")
            response = self.session.get(
                url, 
                headers=headers, 
                cookies=self.cookies,
                timeout=45
            )
            
            if response.status_code == 200:
                # Atualizar cookies da sessão
                self.cookies.update(response.cookies.get_dict())
                
                # Verificar se é uma página de bloqueio disfarçada
                if 'Access Denied' in response.text or 'Forbidden' in response.text:
                    logging.warning("Recebido bloqueio disfarçado como página 200")
                    raise Exception("Bloqueio de acesso detectado")
                
                # Verificar se a página contém anúncios (apenas para páginas de listagem)
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
        """Extrai um ID único do anúncio a partir da URL."""
        if not ad_url:
            return None
        
        try:
            # Tentativa 1: Extrair ID do formato "/item/{id}-titulo-do-anuncio"
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
        """Salva o HTML do anúncio em um arquivo."""
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
        """Extrai os dados relevantes (preço e modelo) de um anúncio."""
        ad_id = self.extract_ad_id(ad_url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Estrutura para armazenar os dados
        ad_data = {
            "id": ad_id,
            "url": ad_url,
            "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        try:
            # 1. EXTRAIR TÍTULO/MODELO (NOVA IMPLEMENTAÇÃO)
            # Buscar pelo título na estrutura de descrição do anúncio
            title_container = soup.select_one('div[data-ds-component="DS-Container"][id="description-title"]')
            
            if title_container:
                # Pegar a primeira div filha
                first_div_child = title_container.select_one('div')
                
                if first_div_child:
                    # Dentro da primeira div filha, pegar o span que contém o título
                    title_span = first_div_child.select_one('span[data-ds-component="DS-Text"]')
                    
                    if title_span:
                        ad_data['modelo'] = title_span.text.strip()
                        logging.info(f"Modelo extraído com sucesso: {ad_data['modelo']}")
                    else:
                        # Tentar pegar qualquer span dentro da primeira div filha
                        any_span = first_div_child.select_one('span')
                        if any_span:
                            ad_data['modelo'] = any_span.text.strip()
                            logging.info(f"Modelo extraído do span alternativo: {ad_data['modelo']}")
            else:
                # Se não encontrou o título em nenhum dos seletores anteriores
                # Procurar em toda descrição pelo que parece ser um modelo de carro
                description = soup.select_one('div[data-section="description"] span.olx-text--body-medium')
                if description:
                    # Pegar a primeira linha que geralmente contém o modelo
                    desc_text = description.text.strip()
                    first_line = desc_text.split('\n')[0]
                    ad_data['modelo'] = first_line
                    logging.info(f"Modelo extraído da descrição: {ad_data['modelo']}")
                else:
                    ad_data['modelo'] = "Modelo não encontrado"
                    logging.warning("Não foi possível encontrar o modelo do veículo")
            
            # 2. EXTRAIR PREÇO FIPE E PREÇO MÉDIO
            preco_fipe= soup.find_all('PREÇO FIPE'):
              
            # Se não encontrou preço FIPE ou preço médio, tentar abordagem alternativa
     
            # Buscar pelos itens de detalhes do anúncio
            details_items = soup.select('div[data-ds-component="DS-AdDetails-item"]')
            
            for item in details_items:
                try:
                    # Cada item tem um par de spans: o primeiro é o rótulo, o segundo é o valor
                    label_span = item.select_one('span:first-child')
                    value_span = item.select_one('span:last-child')
                    
                    if label_span and value_span:
                        label_text = label_span.text.strip().lower()
                        value_text = value_span.text.strip()
                        
                        # Mapeamento para os campos que queremos extrair
                        field_mapping = {
                            'marca': 'marca',
                            'modelo': 'modelo_especifico',
                            'ano': 'ano',
                            'quilometragem': 'quilometragem',
                            'câmbio': 'cambio',
                            'combustível': 'combustivel',
                            'cor': 'cor',
                            'portas': 'portas',
                            'final de placa': 'final_placa'
                        }
                        
                        field_name = field_mapping.get(label_text)
                        if field_name:
                            ad_data[field_name] = value_text
                            logging.debug(f"Detalhe extraído: {field_name}={value_text}")
                except Exception as e:
                    logging.error(f"Erro ao extrair detalhe do item: {e}")
            
            # 5. VERIFICAR SE ENCONTRAMOS DADOS VÁLIDOS E SALVAR PARA DEBUG SE NECESSÁRIO
            if ad_data['modelo'] == "Modelo não encontrado" or ad_data['preco'] == "Preço não encontrado":
                # Salvar HTML para debug quando não encontramos preço ou modelo
                debug_file = os.path.join(self.data_dir, f"debug_extraction_{ad_id}.html")
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                logging.warning(f"Falha na extração completa de dados para anúncio {ad_id}. HTML salvo para debug.")
            
            logging.info(f"Dados extraídos com sucesso para anúncio {ad_id}: {ad_data['modelo']} - {ad_data.get('preco', 'N/A')}")
            return ad_data
            
        except Exception as e:
            logging.error(f"Erro ao extrair dados do anúncio {ad_id}: {e}")
            # Salvar HTML para debug em caso de exceção
            debug_file = os.path.join(self.data_dir, f"debug_error_{ad_id}.html")
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            return ad_data  # Retorna o que conseguiu extrair, mesmo com erro
    
    def process_ad(self, ad_url):
        """Processa um anúncio individual: acessa, extrai dados e salva HTML."""
        ad_id = self.extract_ad_id(ad_url)
        
        if not ad_id:
            logging.warning(f"Não foi possível extrair ID para URL: {ad_url}")
            return False
        
        # Verificar se o anúncio já foi processado
        if ad_id in self.processed_ads:
            logging.debug(f"Anúncio {ad_id} já processado anteriormente.")
            return False
        
        # Fazer requisição para a página do anúncio
        response = self.make_request(ad_url)
        if not response:
            return False
        
        # Salvar o HTML
        html_saved = self.save_ad_html(ad_id, response.text)
        
        # Extrair dados do anúncio
        ad_data = self.extract_ad_data(ad_url, response.text)
        
        # Adicionar aos dados coletados e marcar como processado
        if html_saved:
            self.processed_ads.add(ad_id)
            self.collected_data.append(ad_data)
            logging.info(f"Anúncio {ad_id} processado e salvo com sucesso.")
            return True
        
        return False
    
    def extract_ad_links(self, html_content):
        """Extrai links de anúncios de uma página de resultados."""
        soup = BeautifulSoup(html_content, 'lxml')
        ad_links = []
        logging.info("Extraindo links de anúncios da página...")
        
        # Estratégia 1: Usando os seletores DS-AdCard identificados
        primary_selectors = [
            'section[data-ds-component="DS-AdCard"] a', 
            'div[data-ds-component="DS-AdCard"] a'
        ]
        
        for selector in primary_selectors:
            ad_elements = soup.select(selector)
            if ad_elements:
                logging.info(f"Encontrados {len(ad_elements)} links usando seletor: {selector}")
                for element in ad_elements:
                    href = element.get('href')
                    if href:
                        full_url = urljoin(self.base_url, href)
                        ad_links.append(full_url)
                break
        
        # Se não encontrou links com o seletor principal, tentar alternativas
        if not ad_links:
            logging.info("Usando seletores alternativos para encontrar links...")
            fallback_selectors = [
                'a[data-lurker-detail="list_id"]',
                'div[data-testid="ad-card"] a',
                'a[href*="/item/"]',
                'li[data-testid="listing-card"] a'
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
                    break  # Se encontrou links, não precisa tentar os próximos seletores
        
        # Último recurso: buscar por padrões na URL
        if not ad_links:
            logging.info("Último recurso: buscando links por padrões na URL...")
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if '/item/' in href or ('/autos-e-pecas/carros-vans-e-utilitarios/' in href and not href.endswith('carros-vans-e-utilitarios/')):
                    full_url = urljoin(self.base_url, href)
                    ad_links.append(full_url)
        
        # Filtrar links duplicados e garantir que são links de anúncios
        unique_links = []
        for url in ad_links:
            is_valid = '/item/' in url or ('/autos-e-pecas/carros-vans-e-utilitarios/' in url and not url.endswith('carros-vans-e-utilitarios/'))
            if is_valid and url not in unique_links:
                unique_links.append(url)
        
        logging.info(f"Total de {len(unique_links)} links únicos de anúncios extraídos")
        
        # Se não encontrou links, salvar HTML para debug
        if not unique_links:
            logging.warning("Nenhum link de anúncio encontrado. Salvando HTML para debug")
            with open("debug_no_links_found.html", "w", encoding="utf-8") as f:
                f.write(html_content)
                
            # Analisar a estrutura da página para entender melhor
            with open("debug_page_structure.txt", "w", encoding="utf-8") as f:
                # Verificar todos os elementos que podem conter anúncios
                possible_containers = soup.select('section, div[data-ds], div[data-testid], li')
                f.write(f"Possíveis contêineres: {len(possible_containers)}\n\n")
                
                for i, container in enumerate(possible_containers[:20]):
                    f.write(f"Container {i+1}:\n")
                    f.write(f"Tag: {container.name}\n")
                    f.write(f"Classes: {container.get('class')}\n")
                    f.write(f"Data attrs: {[attr for attr in container.attrs if attr.startswith('data-')]}\n")
                    f.write(f"Links: {len(container.select('a'))}\n\n")
        
        return unique_links
    
    def extract_next_page(self, html_content, current_page):
        """Extrai o link para a próxima página de resultados."""
        soup = BeautifulSoup(html_content, 'lxml')
        
        # Tentativa 1: Botão específico de próxima página
        next_button = soup.find('a', text=lambda t: t and ('Próxima' in t or 'Próximo' in t or 'próxima' in t))
        if next_button and next_button.get('href'):
            return urljoin(self.base_url, next_button['href'])
        
        # Tentativa 2: Botão de paginação com número maior que o atual
        pagination_links = soup.select('a[data-lurker-detail="pagination"]')
        for link in pagination_links:
            try:
                page_num = int(link.text.strip())
                if page_num == current_page + 1:
                    return urljoin(self.base_url, link['href'])
            except (ValueError, AttributeError):
                continue
        
        # Tentativa 3: Construir a URL da próxima página
        next_page = current_page + 1
        return f"{self.base_url}?o={next_page}"
    
    def crawl(self, max_pages=100):
        """Realiza o processo de crawling completo, acessando cada anúncio."""
        current_page = 1
        current_url = self.base_url
        total_ads_processed = 0
        consecutive_errors = 0
        
        try:
            while current_page <= max_pages:
                logging.info(f"Processando página {current_page}: {current_url}")
                
                # Obter conteúdo da página de listagem
                response = self.make_request(current_url)
                if not response:
                    consecutive_errors += 1
                    logging.error(f"Não foi possível acessar a página {current_page}")
                    
                    if consecutive_errors >= 3:
                        logging.error("Muitos erros consecutivos. Pausando por um período maior...")
                        time.sleep(random.uniform(300, 600))  # 5-10 minutos
                        
                        # Reiniciar sessão e tentar novamente
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
                            current_url = f"{self.base_url}?o={current_page}"
                        
                        consecutive_errors = 0
                        continue
                    else:
                        time.sleep(random.uniform(30, 60))  # Espera 30-60 segundos antes de tentar novamente
                        continue
                
                consecutive_errors = 0  # Reinicia contador de erros após sucesso
                
                # Extrair links dos anúncios
                ad_links = self.extract_ad_links(response.text)
                logging.info(f"Encontrados {len(ad_links)} anúncios na página {current_page}")
                
                # Se não encontrou links, a página pode estar vazia ou bloqueada
                if not ad_links:
                    logging.warning(f"Nenhum anúncio encontrado na página {current_page}. Salvando para análise.")
                    
                    # Salvar html para análise
                    with open(f"debug_page_{current_page}.html", "w", encoding="utf-8") as f:
                        f.write(response.text)
                    
                    # Tentar avançar para a próxima página mesmo assim
                    current_page += 1
                    current_url = f"{self.base_url}?o={current_page}"
                    time.sleep(random.uniform(60, 120))  # Espera maior antes de tentar a próxima
                    continue
                
                # Processar cada anúncio
                for ad_url in tqdm(ad_links, desc=f"Página {current_page}"):
                    success = self.process_ad(ad_url)
                    if success:
                        total_ads_processed += 1
                    
                    # Salvar progresso periodicamente
                    if total_ads_processed % 10 == 0:
                        self.save_data()
                    
                    # Espera variável entre anúncios (1-3 segundos)
                    time.sleep(random.uniform(1, 3))
                
                # Encontrar link para próxima página
                next_url = self.extract_next_page(response.text, current_page)
                if not next_url or next_url == current_url:
                    logging.info("Nenhuma próxima página encontrada. Finalizando.")
                    break
                
                current_url = next_url
                current_page += 1
                
                # Espera aleatória entre páginas (mais longa para evitar bloqueios)
                wait_time = random.uniform(15, 30)
                logging.info(f"Aguardando {wait_time:.2f}s antes de acessar a próxima página...")
                time.sleep(wait_time)
                
                # Salvar progresso após cada página
                self.save_data()
        
        except KeyboardInterrupt:
            logging.info("Interrompido pelo usuário.")
        except Exception as e:
            logging.error(f"Erro durante o crawling: {e}", exc_info=True)
        finally:
            # Salvar anúncios processados antes de encerrar
            self.save_data()
            logging.info(f"Crawling finalizado. Total de anúncios processados: {total_ads_processed}")


def parse_olx_ad_page(html_content):
    """
    Extrai dados detalhados de um anúncio individual da OLX
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    logging.info("Analisando página de anúncio individual...")
    
    # Dicionário para armazenar os dados extraídos
    ad_data = {}
    
    try:
        # Título do anúncio
        title_element = (
            soup.select_one('h1[data-ds-component="DS-Text-title"]') or
            soup.select_one('h1.sc-45jt43-0') or
            soup.select_one('h1')
        )
        ad_data['title'] = title_element.text.strip() if title_element else "Título não encontrado"
        
        # Preço
        price_element = (
            soup.select_one('span[data-ds-component="DS-Text-price"]') or
            soup.select_one('h2.sc-1wimjbb-0') or
            soup.select_one('span.ad__sc-1wimjbb-1')
        )
        ad_data['price'] = price_element.text.strip() if price_element else "Preço não encontrado"
        
        # Data de publicação
        date_element = soup.select_one('span.sc-1oq8jzc-0, span[data-ds-component="DS-Text-subtitle"]')
        ad_data['published_date'] = date_element.text.strip() if date_element else ""
        
        # Localização
        location_element = soup.select_one('div.sc-18p038x-0, div[data-ds-component="DS-Text-subtitle"]')
        ad_data['location'] = location_element.text.strip() if location_element else ""
        
        # Código do anúncio
        code_element = soup.select_one('span.sc-5hxmq3-0, span[data-ds-component="DS-Text-regular"]')
        ad_data['ad_code'] = code_element.text.replace('Código', '').strip() if code_element else ""
        
        # Imagens do anúncio
        image_elements = soup.select('img[data-ds-component="DS-Image"], div.sc-1fcmfeb-0 img')
        ad_data['images'] = [img.get('src') for img in image_elements if img.get('src') and not img.get('src').endswith('.svg')]
        
        # Atributos/detalhes do veículo (tabela de especificações)
        details = {}
        detail_elements = soup.select('div.sc-jfmDQi, div[data-ds-component="DS-AdDetails-item"]')
        
        for detail in detail_elements:
            # Buscar o título e valor de cada detalhe
            try:
                label = detail.select_one('dt, span:first-child')
                value = detail.select_one('dd, span:last-child')
                
                if label and value:
                    label_text = label.text.strip().lower()
                    value_text = value.text.strip()
                    
                    # Mapear para campos padronizados
                    field_mapping = {
                        'marca': 'brand',
                        'modelo': 'model',
                        'ano': 'year',
                        'quilometragem': 'mileage',
                        'câmbio': 'transmission',
                        'combustível': 'fuel',
                        'cor': 'color',
                        'final de placa': 'plate_end',
                        'portas': 'doors'
                    }
                    
                    field_name = field_mapping.get(label_text, label_text)
                    details[field_name] = value_text
            except Exception as e:
                logging.error(f"Erro ao extrair detalhe do veículo: {e}")
        
        ad_data['details'] = details
        
        # Descrição do anúncio
        description_element = soup.select_one('div[data-ds-component="DS-AdDescription"], div.sc-bZQynM')
        ad_data['description'] = description_element.text.strip() if description_element else ""
        
        logging.info(f"Anúncio analisado com sucesso: {ad_data['title']}")
        return ad_data
        
    except Exception as e:
        logging.error(f"Erro ao analisar anúncio: {e}")
        return {"error": str(e), "partial_data": ad_data}


def parse_olx_search_page(page_content):
    """
    Extrai dados da página de busca da OLX para apresentar resultados resumidos
    """
    logging.info("Analisando página de busca...")
    soup = BeautifulSoup(page_content, 'html.parser')
    
    # Encontrar os cards de anúncios usando o seletor correto
    items = soup.select('section[data-ds-component="DS-AdCard"], div[data-ds-component="DS-AdCard"]')
    
    logging.info(f"Encontrados {len(items)} anúncios usando seletor DS-AdCard")
    
    # Se não encontrar com o seletor principal, tentar alternativas
    if not items:
        selectors = [
            'li[data-testid="listing-card"]',
            'div[data-testid="ad-card"]',
            'li.sc-1fcmfeb-2', 
            'div.sc-1fcmfeb-1 > div'
        ]
        
        for selector in selectors:
            items = soup.select(selector)
            if items:
                logging.info(f"Encontrados {len(items)} anúncios usando seletor alternativo: {selector}")
                break
    
    # Salvar estrutura para debug
    with open("debug_search_structure.txt", "w", encoding="utf-8") as f:
        f.write(f"Total de anúncios encontrados: {len(items)}\n\n")
        
        for i, item in enumerate(items[:5]):
            f.write(f"Anúncio {i+1}:\n")
            f.write(f"Classes: {item.get('class')}\n")
            f.write(f"Data attributes: {[attr for attr in item.attrs if attr.startswith('data-')]}\n")
            
            links = item.select('a')
            f.write(f"Links encontrados: {len(links)}\n")
            for j, link in enumerate(links):
                f.write(f"  Link {j+1}: {link.get('href')}\n")
            
            f.write(f"HTML parcial:\n{str(item)[:300]}...\n\n")
    
    parsed_items = []
    for item in items:
        try:
            # Link do anúncio
            link_element = item.select_one('a')
            link = link_element.get('href') if link_element else ""
            
            if link and not link.startswith('http'):
                link = f"https://www.olx.com.br{link}"
            
            # Título
            title_element = (
                item.select_one('h2') or 
                item.select_one('span[data-ds-component="DS-Text-primary"]') or
                item.select_one('*[class*="title"]')
            )
            title = title_element.text.strip() if title_element else "Título não encontrado"
            
            # Preço
            price_element = (
                item.select_one('span[data-testid="ad-price"]') or
                item.select_one('span[data-ds-component="DS-Text-primary"][data-testid="ad-price"]') or
                item.select_one('*[class*="price"]')
            )
            price = price_element.text.strip() if price_element else "Preço não encontrado"
            
            # Localização
            location_element = (
                item.select_one('*[data-testid="ad-location"]') or
                item.select_one('span[data-ds-component="DS-Text-secondary"]') or
                item.select_one('*[class*="location"]')
            )
            location = location_element.text.strip() if location_element else "Local não encontrado"
            
            # Imagem
            img_element = item.select_one('img')
            image_url = img_element.get('src') or img_element.get('data-src') if img_element else ""
            
            # Data de publicação
            date_element = item.select_one('*[class*="date"], span[data-ds-component="DS-Text-secondary"]:last-child')
            published_date = date_element.text.strip() if date_element else ""
            
            parsed_item = {
                'title': title,
                'price': price,
                'link': link,
                'location': location,
                'image_url': image_url,
                'published_date': published_date
            }
            
            if link:  # Adicionar apenas se tiver um link válido
                parsed_items.append(parsed_item)
                logging.info(f"Item analisado: {title} - {price}")
            
        except Exception as e:
            logging.error(f"Erro ao analisar item: {e}")
            continue
    
    logging.info(f"Total de {len(parsed_items)} anúncios analisados com sucesso")
    return parsed_items

# Para executar o crawler
if __name__ == "__main__":
    try:
        crawler = OlxCrawler()
        crawler.crawl(max_pages=100)
    except Exception as e:
        logging.error(f"Erro ao executar crawler: {e}", exc_info=True)