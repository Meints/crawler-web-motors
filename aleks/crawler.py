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

# Constantes para seletores HTML
TITULO_SELECTOR = 'h1.olx-text--title-large, h1.olx-text--title-xlarge, h1.olx-ad-title, span[data-testid="ad-title"]'
DETALHES_CONTAINER_SELECTOR = 'div.ad__sc-2h9gkk-0.dLQbjb'
DETALHES_ALTERNATIVOS_SELECTOR_1 = 'div[data-ds-component="DS-AdDetails"] div[data-testid="ad-properties-item"]'
DETALHES_ALTERNATIVOS_SELECTOR_2 = 'div[data-testid="ad-properties"] div[data-testid="ad-properties-item"], div[data-testid="properties-card"] div[data-testid="ad-properties-item"]'
PRECO_CONTAINER_SELECTOR = 'div#price-box-container'
PRECO_SPAN_SELECTOR = 'span.olx-text--title-large, span[class*="title-large"]'
PRECO_ALTERNATIVO_SELECTOR = 'div[data-testid="ad-price-wrapper"] span, span[data-ds-component="DS-Text"][class*="olx-text--title"]'
PRECO_REGEX_PATTERN = r'R\$\s*[\d.,]+'

# Constantes para tempo de espera (em segundos)
TEMPO_ESPERA_REQUISICAO = (0.2, 2)
TEMPO_ESPERA_SESSAO_INICIAL = (2, 5)
TEMPO_ESPERA_CATEGORIA = (3, 7)
TEMPO_ESPERA_APOS_BLOQUEIO = (120, 300)
TEMPO_ESPERA_APOS_403 = (60, 180)
TEMPO_ESPERA_ENTRE_ANUNCIOS = (1, 3)
TEMPO_ESPERA_PROXIMA_PAGINA = (15, 30)
TEMPO_ESPERA_PROXIMO_ESTADO = (60, 180)
TEMPO_ESPERA_ERROS_CONSECUTIVOS = (300, 600)  # 5-10 minutos
TEMPO_ESPERA_SEM_ANUNCIOS = (60, 120)

# Seletores para links de anúncios
SELETORES_ANUNCIOS_PRIMARIOS = [
    'a[data-testid="adcard-link"]',  # Novo seletor principal da OLX (2024)
    'a.AdCard_link__4c7W6',  # Seletor de classe do card de anúncio
    'a[href*="/autos-e-pecas/carros-vans-e-utilitarios/"][href*="-"]', # Links de anúncios específicos
    'a[data-testid="ad-card-link"]',  # Outro seletor possível
    'div[data-testid="listing-card"] a', # Seletor alternativo
    'a[data-ds-component="DS-Link"][href*="/item"]', # Formato de link
    'div[data-testid="ad-card"] a',
    'section[data-ds-component="DS-AdCard"] a',
    'div[data-ds-component="DS-AdCard"] a'
]

SELETORES_ANUNCIOS_ALTERNATIVOS = [
    'a[href*="/item/"]',  # Links de item genérico
    'a[data-lurker-detail="list_id"]',  # Seletor antigo
    'a[href*="olx.com.br/autos-e-pecas/carros"]',  # Links diretos para carros
    'a.olx-ad-card__link-wrapper',  # Classe específica de cards
    'a[href*="carros-vans-e-utilitarios/"]'  # Padrão de URL para carros
]

# Lista de marcas comuns para extração do título
MARCAS_COMUNS = ['honda', 'toyota', 'volkswagen', 'vw', 'fiat', 'chevrolet', 'ford', 'hyundai', 'nissan', 'renault']

class OlxCrawler:
    def __init__(self):
        # Mapeamento de siglas de estados para nomes completos
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
        self.estado_atual = None
        
        self.diretorio_script = os.path.dirname(os.path.abspath(__file__))
        self.diretorio_dados = os.path.join(self.diretorio_script, "data")
        self.diretorio_html = os.path.join(self.diretorio_dados, "html")
        self.arquivo_json = os.path.join(self.diretorio_dados, "anuncios.json")
        
        self.anuncios_processados = set()  
        self.dados_coletados = []  
        
        self.sessao = self._criar_sessao_http()
        
        self.cookies = self._obter_cookies_iniciais()
        
        self._criar_diretorios()
        
        self._carregar_dados_salvos()
    
    def _criar_sessao_http(self):
        """Cria uma nova sessão HTTP com CloudScraper"""
        return cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            },
            delay=10
        )
    
    def _obter_cookies_iniciais(self):
        """Retorna os cookies iniciais para a sessão"""
        return {
            'onboarding_olx': 'true',
            'language': 'pt-BR',
            'hasSeenLoginModal': 'true',
        }
    
    def _criar_diretorios(self):
        """Cria os diretórios necessários para armazenamento"""
        if not os.path.exists(self.diretorio_dados):
            os.makedirs(self.diretorio_dados)
        
        if not os.path.exists(self.diretorio_html):
            os.makedirs(self.diretorio_html)
    
    def _carregar_dados_salvos(self):
        """Carrega dados de execuções anteriores"""
        self._carregar_anuncios_processados()
        self._carregar_dados_coletados()
    
    def _carregar_anuncios_processados(self):
        """Carrega IDs de anúncios já processados anteriormente"""
        arquivo_processados = os.path.join(self.diretorio_dados, "processed_ads.json")
        if os.path.exists(arquivo_processados):
            try:
                with open(arquivo_processados, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    self.anuncios_processados = set(dados.get("processed_ids", []))
                logging.info(f"Carregados {len(self.anuncios_processados)} anúncios processados anteriormente.")
            except Exception as e:
                logging.error(f"Erro ao carregar anúncios processados: {e}")
                self.anuncios_processados = set()
    
    def _carregar_dados_coletados(self):
        """Carrega dados de anúncios já coletados anteriormente"""
        if os.path.exists(self.arquivo_json):
            try:
                with open(self.arquivo_json, 'r', encoding='utf-8') as f:
                    self.dados_coletados = json.load(f)
                logging.info(f"Carregados {len(self.dados_coletados)} anúncios do arquivo JSON.")
            except Exception as e:
                logging.error(f"Erro ao carregar dados dos anúncios: {e}")
                self.dados_coletados = []
    
    def salvar_dados(self):
        """Salva todos os dados coletados em arquivos"""
        self._salvar_anuncios_processados()
        self._salvar_dados_coletados()
    
    def _salvar_anuncios_processados(self):
        """Salva a lista de IDs de anúncios processados"""
        arquivo_processados = os.path.join(self.diretorio_dados, "processed_ads.json")
        try:
            with open(arquivo_processados, 'w', encoding='utf-8') as f:
                json.dump({"processed_ids": list(self.anuncios_processados)}, f)
            logging.info(f"Salvos {len(self.anuncios_processados)} IDs de anúncios processados.")
        except Exception as e:
            logging.error(f"Erro ao salvar anúncios processados: {e}")
    
    def _salvar_dados_coletados(self):
        """Salva os dados coletados dos anúncios em JSON"""
        try:
            with open(self.arquivo_json, 'w', encoding='utf-8') as f:
                json.dump(self.dados_coletados, f, ensure_ascii=False, indent=2)
            logging.info(f"Salvos {len(self.dados_coletados)} anúncios no arquivo JSON.")
        except Exception as e:
            logging.error(f"Erro ao salvar dados dos anúncios: {e}")
    
    def gerar_headers_http(self):
        """Gera cabeçalhos HTTP aleatórios para evitar detecção"""
        versao_chrome = f"{random.randint(90, 110)}.0.{random.randint(1000, 5000)}.{random.randint(10, 200)}"
        
        return {
            'User-Agent': f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{versao_chrome} Safari/537.36',
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
            'sec-ch-ua': f'"Google Chrome";v="{versao_chrome.split(".")[0]}", "Chromium";v="{versao_chrome.split(".")[0]}"',
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
    def fazer_requisicao(self, url):
        """Realiza uma requisição HTTP com tratamento de erros e backoff"""
        tempo_espera = random.uniform(*TEMPO_ESPERA_REQUISICAO)
        logging.info(f"Aguardando {tempo_espera:.2f}s antes da requisição...")
        time.sleep(tempo_espera)
        
        headers = self.gerar_headers_http()
        
        try:
            self._inicializar_sessao_se_necessario(headers)
            self._visitar_categoria_intermediaria(headers)
            
            logging.info(f"Acessando URL: {url}")
            response = self.sessao.get(
                url, 
                headers=headers, 
                cookies=self.cookies,
                timeout=45
            )
            
            return self._processar_resposta_http(response, url)
                
        except Exception as e:
            return self._tratar_erro_requisicao(e, url)
    
    def _inicializar_sessao_se_necessario(self, headers):
        """Inicializa a sessão com cookies se necessário"""
        if 'olx.com.br' not in self.sessao.cookies.get_dict():
            logging.info("Inicializando sessão com página inicial...")
            self.sessao.get('https://www.olx.com.br/', headers=headers, timeout=30)
            time.sleep(random.uniform(*TEMPO_ESPERA_SESSAO_INICIAL))
    
    def _visitar_categoria_intermediaria(self, headers):
        """Visita aleatoriamente uma categoria intermediária para simular navegação humana"""
        if random.random() > 0.5:
            url_categoria = 'https://www.olx.com.br/autos-e-pecas'
            logging.info(f"Acessando categoria intermediária: {url_categoria}")
            self.sessao.get(url_categoria, headers=headers, timeout=30)
            time.sleep(random.uniform(*TEMPO_ESPERA_CATEGORIA))
    
    def _processar_resposta_http(self, response, url):
        """Processa a resposta HTTP e verifica possíveis bloqueios"""
        if response.status_code == 200:
            self.cookies.update(response.cookies.get_dict())
            
            # Verifica se é um bloqueio disfarçado como página 200
            if 'Access Denied' in response.text or 'Forbidden' in response.text:
                logging.warning("Recebido bloqueio disfarçado como página 200")
                raise Exception("Bloqueio de acesso detectado")
            
            # Verifica se a página de listagem tem anúncios
            if 'carros-vans-e-utilitarios' in url and '?' in url:
                self._verificar_presenca_anuncios(response)
            
            return response
        else:
            logging.warning(f"Resposta não-200: {response.status_code} para URL: {url}")
            if response.status_code == 403:
                logging.error("Bloqueio detectado! Esperando tempo maior...")
                time.sleep(random.uniform(*TEMPO_ESPERA_APOS_403))
            return None
    
    def _verificar_presenca_anuncios(self, response):
        """Verifica se a página de listagem contém cards de anúncios"""
        soup = BeautifulSoup(response.text, 'lxml')
        seletores_esperados = [
            'section[data-ds-component="DS-AdCard"]',
            'div[data-ds-component="DS-AdCard"]',
            'div[data-testid="ad-card"]'
        ]
        
        has_ads = any(len(soup.select(selector)) > 0 for selector in seletores_esperados)
        
        if not has_ads:
            logging.warning("Página não contém cards de anúncios esperados")
    
    def _tratar_erro_requisicao(self, exception, url):
        """Trata exceções durante requisições HTTP"""
        logging.error(f"Erro na requisição para {url}: {exception}")
        if "Bloqueio de acesso detectado" in str(exception):
            time.sleep(random.uniform(*TEMPO_ESPERA_APOS_BLOQUEIO))
        return None
    
    def extrair_id_anuncio(self, url_anuncio):
        """Extrai o ID único do anúncio a partir da URL"""
        if not url_anuncio:
            return None
        
        try:
            # Tentar extrair ID do caminho da URL
            partes_caminho = urlparse(url_anuncio).path.split('/')
            for parte in partes_caminho:
                if parte.startswith('id-'):
                    return parte
                
                # Extrair parte numérica no início que pode ser um ID
                if parte and parte[0].isdigit():
                    parte_numerica = self._extrair_prefixo_numerico(parte)
                    if parte_numerica and len(parte_numerica) > 5:
                        return parte_numerica
            
            # Usar hash da URL como último recurso
            return hashlib.md5(url_anuncio.encode()).hexdigest()
            
        except Exception as e:
            logging.error(f"Erro ao extrair ID do anúncio {url_anuncio}: {e}")
            return hashlib.md5(url_anuncio.encode()).hexdigest()
    
    def _extrair_prefixo_numerico(self, texto):
        """Extrai apenas caracteres numéricos do início de um texto"""
        prefixo_numerico = ''
        for char in texto:
            if char.isdigit():
                prefixo_numerico += char
            else:
                break
        return prefixo_numerico
    
    def salvar_html_anuncio(self, id_anuncio, conteudo_html):
        """Salva o conteúdo HTML de um anúncio em arquivo"""
        if not id_anuncio:
            return False
        
        nome_arquivo = os.path.join(self.diretorio_html, f"ad_{id_anuncio}.html")
        try:
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                f.write(conteudo_html)
            return True
        except Exception as e:
            logging.error(f"Erro ao salvar HTML do anúncio {id_anuncio}: {e}")
            return False
    
    def extrair_dados_anuncio(self, url_anuncio, conteudo_html):
        """Extrai todos os dados estruturados de um anúncio a partir do HTML"""
        id_anuncio = self.extrair_id_anuncio(url_anuncio)
        soup = BeautifulSoup(conteudo_html, 'html.parser')
        
        # Inicializa estrutura básica de dados do anúncio
        dados_anuncio = {
            "id": id_anuncio,
            "url": url_anuncio,
            "data_extracao": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "estado": self.estados.get(self.estado_atual, self.estado_atual)
        }
        
        try:
            logging.info(f"Iniciando extração de dados para anúncio {id_anuncio}")
            
            # Extração de detalhes do veículo
            self._extrair_detalhes_veiculo(soup, dados_anuncio)
            
            # Extração de preço
            self._extrair_preco_anuncio(soup, dados_anuncio)
            
            # Verificação da qualidade dos dados extraídos
            if dados_anuncio.get('modelo') == "Modelo não encontrado":
                self._salvar_debug_extracao(id_anuncio, conteudo_html)
            
            logging.info(f"Dados extraídos com sucesso para anúncio {id_anuncio}: {dados_anuncio.get('modelo')} - {dados_anuncio.get('preco', 'N/A')}")
            return dados_anuncio
            
        except Exception as e:
            logging.error(f"Erro ao extrair dados do anúncio {id_anuncio}: {e}")
            self._salvar_debug_erro(id_anuncio, conteudo_html)
            return dados_anuncio

    def _extrair_detalhes_veiculo(self, soup, dados_anuncio):
        """Extrai os detalhes do veículo (marca, ano, km, etc)"""
        # Extração pela seção de detalhes principal
        secao_detalhes = soup.select_one('div#details')
        containers_detalhes = []
        
        if secao_detalhes:
            logging.info("Seção de detalhes encontrada pelo ID")
            containers_detalhes = secao_detalhes.select(DETALHES_CONTAINER_SELECTOR)
        
        if containers_detalhes:
            # Processa cada container de detalhes
            self._processar_containers_detalhes(containers_detalhes, dados_anuncio)
        else:
            # Tenta métodos alternativos se não encontrar os containers padrão
            self._tentar_extrair_detalhes_alternativos(soup, dados_anuncio)
    
    def _processar_containers_detalhes(self, containers, dados_anuncio):
        """Processa os containers de detalhes do veículo"""
        logging.info(f"Encontrados {len(containers)} containers de detalhes do anúncio")
        
        for container in containers:
            try:
                # Extrai etiqueta (label) e valor de cada detalhe
                elemento_label = container.select_one('span[data-variant="overline"]')
                if not elemento_label:
                    continue
                
                texto_label = elemento_label.text.strip().lower()
                logging.info(f"Processando detalhe: {texto_label}")
                
                elemento_valor = container.select_one('a.olx-link, span.ekhFnR, span:not([data-variant])')
                if not elemento_valor:
                    continue
                
                texto_valor = elemento_valor.text.strip()
                
                # Mapeia os diferentes tipos de detalhes para as chaves do dicionário
                if 'marca' in texto_label:
                    dados_anuncio['marca'] = texto_valor
                    logging.info(f"Marca encontrada: {texto_valor}")
                elif 'modelo' in texto_label:
                    dados_anuncio['modelo'] = texto_valor
                    logging.info(f"Modelo encontrado nos detalhes: {texto_valor}")
                elif 'tipo de veículo' in texto_label:
                    dados_anuncio['tipo_veiculo'] = texto_valor
                    logging.info(f"Tipo de veículo: {texto_valor}")
                elif 'ano' in texto_label:
                    dados_anuncio['ano'] = texto_valor
                    logging.info(f"Ano: {texto_valor}")
                elif 'quilometragem' in texto_label:
                    dados_anuncio['quilometragem'] = texto_valor
                    logging.info(f"Quilometragem: {texto_valor}")
                elif 'potência do motor' in texto_label:
                    dados_anuncio['potencia'] = texto_valor
                    logging.info(f"Potência do motor: {texto_valor}")
                elif 'combustível' in texto_label:
                    dados_anuncio['combustivel'] = texto_valor
                    logging.info(f"Combustível: {texto_valor}")
                elif 'câmbio' in texto_label:
                    dados_anuncio['cambio'] = texto_valor
                    logging.info(f"Câmbio: {texto_valor}")
                elif 'direção' in texto_label or 'tipo de direção' in texto_label:
                    dados_anuncio['direcao'] = texto_valor
                    logging.info(f"Direção: {texto_valor}")
                elif 'cor' in texto_label:
                    dados_anuncio['cor'] = texto_valor
                    logging.info(f"Cor: {texto_valor}")
                elif 'portas' in texto_label:
                    dados_anuncio['portas'] = texto_valor
                    logging.info(f"Portas: {texto_valor}")
                elif 'final de placa' in texto_label:
                    dados_anuncio['final_placa'] = texto_valor
                    logging.info(f"Final de placa: {texto_valor}")
                elif 'gnv' in texto_label:
                    dados_anuncio['gnv'] = texto_valor
                    logging.info(f"Possui GNV: {texto_valor}")
                elif 'categoria' in texto_label:
                    dados_anuncio['categoria'] = texto_valor
                    logging.info(f"Categoria: {texto_valor}")
            except Exception as erro_detalhe:
                logging.error(f"Erro ao extrair detalhe: {erro_detalhe}")
    
    def _tentar_extrair_detalhes_alternativos(self, soup, dados_anuncio):
        """Tenta métodos alternativos para extrair detalhes do veículo"""
        logging.warning("Detalhes não encontrados na seção principal, tentando métodos alternativos")
        
        # Tenta pelos seletores alternativos
        elementos_detalhe = soup.select(DETALHES_ALTERNATIVOS_SELECTOR_1)
        if not elementos_detalhe:
            elementos_detalhe = soup.select(DETALHES_ALTERNATIVOS_SELECTOR_2)
        
        if elementos_detalhe:
            self._processar_elementos_detalhe_alternativos(elementos_detalhe, dados_anuncio)
        
        # Tenta extrair a marca do breadcrumb
        self._extrair_marca_do_breadcrumb(soup, dados_anuncio)
        
        # Se ainda não tiver marca, tentar extrair do título
        self._tentar_extrair_marca_do_titulo(dados_anuncio)
    
    def _processar_elementos_detalhe_alternativos(self, elementos_detalhe, dados_anuncio):
        """Processa os elementos de detalhe em formato alternativo"""
        logging.info(f"Encontrados {len(elementos_detalhe)} elementos de detalhes alternativos")
        for detalhe in elementos_detalhe:
            try:
                label = detalhe.select_one('span.olx-text--caption')
                valor = detalhe.select_one('span.olx-text--body-large, span.olx-text--body, span:not(.olx-text--caption), a')
                
                if label and valor:
                    texto_label = label.text.strip().lower()
                    texto_valor = valor.text.strip()
                    
                    if 'marca' in texto_label:
                        dados_anuncio['marca'] = texto_valor
                    elif 'modelo' in texto_label and not dados_anuncio.get('modelo'):
                        dados_anuncio['modelo'] = texto_valor
                    # Outros mapeamentos de detalhes poderiam ser adicionados aqui
            except Exception as e:
                logging.error(f"Erro ao extrair detalhe alternativo: {e}")
    
    def _extrair_marca_do_breadcrumb(self, soup, dados_anuncio):
        """Tenta extrair a marca do veículo do breadcrumb da página"""
        breadcrumb = soup.select('ol[data-testid="breadcrumb"] li a')
        if breadcrumb and len(breadcrumb) >= 3:
            possivel_marca = breadcrumb[2].text.strip()
            dados_anuncio['marca'] = possivel_marca
            logging.info(f"Marca extraída do breadcrumb: {possivel_marca}")
    
    def _tentar_extrair_marca_do_titulo(self, dados_anuncio):
        """Tenta extrair a marca do veículo a partir do título/modelo"""
        if not dados_anuncio.get('marca') and dados_anuncio.get('modelo'):
            primeira_palavra = dados_anuncio['modelo'].split()[0]
            if primeira_palavra.lower() in MARCAS_COMUNS:
                dados_anuncio['marca'] = primeira_palavra
                logging.info(f"Marca extraída do título: {primeira_palavra}")
            else:
                dados_anuncio['marca'] = "Marca não encontrada"
    
    def _extrair_preco_anuncio(self, soup, dados_anuncio):
        """Extrai o preço do anúncio usando várias estratégias"""
        try:
            logging.info("Extraindo preço do anúncio...")
            
            # Estratégia 1: Container específico de preço
            container_preco = soup.select_one(PRECO_CONTAINER_SELECTOR)
            if container_preco:
                logging.info("Encontrado container de preço específico")
                span_preco = container_preco.select_one(PRECO_SPAN_SELECTOR)
                
                if span_preco and 'R$' in span_preco.text:
                    preco_valor = span_preco.text.strip()
                    logging.info(f"Preço encontrado no price-box-container: {preco_valor}")
                    dados_anuncio['preco'] = preco_valor
                else:
                    # Busca por regex de preço no container
                    texto_preco = re.search(PRECO_REGEX_PATTERN, container_preco.text)
                    if texto_preco:
                        preco_valor = texto_preco.group(0).strip()
                        logging.info(f"Preço encontrado com regex no price-box-container: {preco_valor}")
                        dados_anuncio['preco'] = preco_valor
            else:
                # Estratégia 2: Seletores alternativos
                self._extrair_preco_por_seletores_alternativos(soup, dados_anuncio)
        
        except Exception as e:
            logging.error(f"Erro ao extrair preço: {e}")
            dados_anuncio['preco'] = "Erro na extração"
    
    def _extrair_preco_por_seletores_alternativos(self, soup, dados_anuncio):
        """Extrai preço usando seletores alternativos e busca por padrão de preço"""
        elemento_preco = soup.select_one(PRECO_ALTERNATIVO_SELECTOR)
        if elemento_preco and 'R$' in elemento_preco.text:
            preco_valor = elemento_preco.text.strip()
            logging.info(f"Preço encontrado no elemento alternativo: {preco_valor}")
            dados_anuncio['preco'] = preco_valor
        else:
            # Busca por padrão de preço em qualquer elemento
            padrao_preco = re.compile(PRECO_REGEX_PATTERN)
            for elemento in soup.find_all(['span', 'div', 'p']):
                if elemento.text and padrao_preco.search(elemento.text):
                    preco_valor = padrao_preco.search(elemento.text).group(0).strip()
                    logging.info(f"Preço encontrado com regex: {preco_valor}")
                    dados_anuncio['preco'] = preco_valor
                    break
            else:
                logging.warning("Preço não encontrado no anúncio")
                dados_anuncio['preco'] = "Preço não encontrado"
    
    def _salvar_debug_extracao(self, id_anuncio, conteudo_html):
        """Salva HTML para debug quando falha na extração do modelo"""
        arquivo_debug = os.path.join(self.diretorio_dados, f"debug_extraction_{id_anuncio}.html")
        with open(arquivo_debug, 'w', encoding='utf-8') as f:
            f.write(conteudo_html)
        logging.warning(f"Falha na extração completa de dados para anúncio {id_anuncio}. HTML salvo para debug.")
    
    def _salvar_debug_erro(self, id_anuncio, conteudo_html):
        """Salva HTML para debug quando ocorre erro na extração"""
        arquivo_debug = os.path.join(self.diretorio_dados, f"debug_error_{id_anuncio}.html")
        with open(arquivo_debug, 'w', encoding='utf-8') as f:
            f.write(conteudo_html)
    
    def processar_anuncio(self, url_anuncio):
        """Processa um anúncio: baixa HTML, extrai e salva dados"""
        id_anuncio = self.extrair_id_anuncio(url_anuncio)
        
        if not id_anuncio:
            logging.warning(f"Não foi possível extrair ID para URL: {url_anuncio}")
            return False
        
        if id_anuncio in self.anuncios_processados:
            logging.debug(f"Anúncio {id_anuncio} já processado anteriormente.")
            return False
        
        response = self.fazer_requisicao(url_anuncio)
        if not response:
            return False
        
        html_salvo = self.salvar_html_anuncio(id_anuncio, response.text)
        
        dados_anuncio = self.extrair_dados_anuncio(url_anuncio, response.text)
        
        if html_salvo:
            self.anuncios_processados.add(id_anuncio)
            self.dados_coletados.append(dados_anuncio)
            logging.info(f"Anúncio {id_anuncio} processado e salvo com sucesso.")
            return True
        
        return False
    
    def extrair_links_anuncios(self, conteudo_html):
        """Extrai links de anúncios de uma página de listagem"""
        soup = BeautifulSoup(conteudo_html, 'lxml')
        links_anuncio = []
        logging.info("Extraindo links de anúncios da página...")
        
        # Tenta os seletores primários primeiro
        for seletor in SELETORES_ANUNCIOS_PRIMARIOS:
            elementos_anuncio = soup.select(seletor)
            if elementos_anuncio:
                logging.info(f"Encontrados {len(elementos_anuncio)} links usando seletor: {seletor}")
                for elemento in elementos_anuncio:
                    href = elemento.get('href')
                    if href:
                        url_completa = urljoin("https://www.olx.com.br", href)
                        links_anuncio.append(url_completa)
                if links_anuncio:  # Se encontrou links, interrompe a busca
                    break
        
        # Se não encontrou com seletores primários, tenta seletores alternativos
        if not links_anuncio:
            self._tentar_seletores_alternativos(soup, links_anuncio)
        
        # Último recurso: busca por padrões de URL em todos os links
        if not links_anuncio:
            self._buscar_links_por_padrao_url(soup, links_anuncio)
        
        # Filtrar links únicos e válidos
        links_unicos = self._filtrar_links_unicos_validos(links_anuncio)
        
        logging.info(f"Total de {len(links_unicos)} links únicos de anúncios extraídos")
        
        # Se não encontrou nenhum link, salva debug
        if not links_unicos:
            self._salvar_debug_links_nao_encontrados(conteudo_html, soup)
        
        return links_unicos
    
    def _tentar_seletores_alternativos(self, soup, links_anuncio):
        """Tenta encontrar links de anúncios usando seletores alternativos"""
        logging.info("Usando seletores alternativos para encontrar links...")
        
        for seletor in SELETORES_ANUNCIOS_ALTERNATIVOS:
            elementos = soup.select(seletor)
            if elementos:
                logging.info(f"Encontrados {len(elementos)} links usando seletor alternativo: {seletor}")
                for elemento in elementos:
                    href = elemento.get('href')
                    if href:
                        url_completa = urljoin(self.base_url_template.format(estado=self.estado_atual), href)
                        links_anuncio.append(url_completa)
                if links_anuncio:  # Se encontrou links, interrompe a busca
                    break
    
    def _buscar_links_por_padrao_url(self, soup, links_anuncio):
        """Busca por links que correspondam a padrões de URL de anúncios"""
        logging.info("Último recurso: buscando todos os links e filtrando por padrões relevantes...")
        todos_links = soup.find_all('a', href=True)
        
        for link in todos_links:
            href = link['href']
            # Verifica se o link corresponde a padrões de URL de anúncios
            if (
                '/item/' in href or 
                ('/autos-e-pecas/carros-vans-e-utilitarios/' in href and not href.endswith('carros-vans-e-utilitarios/')) or
                ('/anuncio/' in href) or
                ('/d/' in href and 'carros' in href)
            ):
                url_completa = urljoin(self.base_url_template.format(estado=self.estado_atual), href)
                links_anuncio.append(url_completa)
    
    def _filtrar_links_unicos_validos(self, links_anuncio):
        """Filtra lista de links para manter apenas os únicos e válidos"""
        links_unicos = []
        for url in links_anuncio:
            # Verifica se o link é válido segundo os critérios
            eh_valido = (
                '/item/' in url or 
                '/anuncio/' in url or
                ('/d/' in url and 'carros' in url) or
                ('/autos-e-pecas/carros-vans-e-utilitarios/' in url and not url.endswith('carros-vans-e-utilitarios/'))
            )
            if eh_valido and url not in links_unicos:
                links_unicos.append(url)
        
        return links_unicos
    
    def _salvar_debug_links_nao_encontrados(self, conteudo_html, soup):
        """Salva informações de debug quando nenhum link de anúncio é encontrado"""
        logging.warning("Nenhum link de anúncio encontrado. Salvando HTML para debug")
        with open("debug_no_links_found.html", "w", encoding="utf-8") as f:
            f.write(conteudo_html)
            
        with open("debug_page_structure.txt", "w", encoding="utf-8") as f:
            possiveis_containers = soup.select('section, div[data-ds], div[data-testid], li, a[href*="/item/"], a[href*="olx.com.br/"]')
            f.write(f"Possíveis contêineres: {len(possiveis_containers)}\n\n")
            
            for i, container in enumerate(possiveis_containers[:30]):
                f.write(f"Container {i+1}:\n")
                f.write(f"Tag: {container.name}\n")
                f.write(f"Classes: {container.get('class')}\n")
                f.write(f"Data attrs: {[attr for attr in container.attrs if attr.startswith('data-')]}\n")
                if container.name == 'a':
                    f.write(f"Href: {container.get('href')}\n")
                f.write(f"Links: {len(container.select('a'))}\n\n")
    
    def construir_url_proxima_pagina(self, pagina_atual):
        """Constrói a URL da próxima página a partir da página atual"""
        proxima_pagina = pagina_atual + 1
        
        # Usa a URL base do estado atual
        url_base = self.base_url_template.format(estado=self.estado_atual)
        
        # Constrói URL com parâmetro de paginação
        url_proxima = f"{url_base}?o={proxima_pagina}"
        
        logging.info(f"Próxima página construída manualmente: {url_proxima}")
        return url_proxima
    
    def rastrear_estado(self, estado, max_paginas=100):
        """Executa o rastreamento para um estado específico"""
        self.estado_atual = estado
        url_base = self.base_url_template.format(estado=estado)
        pagina_atual = 1
        url_atual = url_base
        total_anuncios_processados = 0
        erros_consecutivos = 0
        
        nome_estado = self.estados.get(estado, estado)
        logging.info(f"Iniciando crawler para o estado: {nome_estado}")
        
        try:
            while pagina_atual <= max_paginas:
                logging.info(f"Processando página {pagina_atual} de {nome_estado}: {url_atual}")
                
                response = self.fazer_requisicao(url_atual)
                if not response:
                    erros_consecutivos += 1
                    logging.error(f"Não foi possível acessar a página {pagina_atual}")
                    
                    if erros_consecutivos >= 3:
                        self._tratar_muitos_erros_consecutivos(estado, pagina_atual, url_base)
                        erros_consecutivos = 0
                        continue
                    else:
                        time.sleep(random.uniform(30, 60))  # Espera 30-60 segundos antes de tentar novamente
                        continue
                
                erros_consecutivos = 0  # Reinicia contador de erros após sucesso
                
                links_anuncio = self.extrair_links_anuncios(response.text)
                logging.info(f"Encontrados {len(links_anuncio)} anúncios na página {pagina_atual} de {nome_estado}")
                
                if not links_anuncio:
                    pagina_atual = self._tratar_pagina_sem_anuncios(estado, pagina_atual, url_base)
                    url_atual = f"{url_base}?o={pagina_atual}"
                    continue
                
                total_anuncios_processados = self._processar_anuncios_da_pagina(
                    links_anuncio, pagina_atual, nome_estado, total_anuncios_processados
                )
                
                url_proxima = self.construir_url_proxima_pagina(pagina_atual)
                if not url_proxima or url_proxima == url_atual:
                    logging.info(f"Nenhuma próxima página encontrada para {nome_estado}. Finalizando.")
                    break
                
                url_atual = url_proxima
                pagina_atual += 1
                
                tempo_espera = random.uniform(*TEMPO_ESPERA_PROXIMA_PAGINA)
                logging.info(f"Aguardando {tempo_espera:.2f}s antes de acessar a próxima página...")
                time.sleep(tempo_espera)
                
                self.salvar_dados()
                
        except KeyboardInterrupt:
            logging.info("Interrompido pelo usuário.")
            return total_anuncios_processados
        except Exception as e:
            logging.error(f"Erro durante o rastreamento do estado {nome_estado}: {e}", exc_info=True)
            return total_anuncios_processados
        
        logging.info(f"Rastreamento do estado {nome_estado} finalizado. Total de anúncios processados: {total_anuncios_processados}")
        return total_anuncios_processados
    
    def _tratar_muitos_erros_consecutivos(self, estado, pagina_atual, url_base):
        """Trata situação de muitos erros consecutivos"""
        logging.error("Muitos erros consecutivos. Pausando por um período maior...")
        time.sleep(random.uniform(*TEMPO_ESPERA_ERROS_CONSECUTIVOS))
        
        logging.info("Reiniciando sessão...")
        self.sessao = self._criar_sessao_http()
        
        # Em caso de muitos erros, tentar URL alternativa
        if pagina_atual > 1:
            return f"{url_base}?o={pagina_atual}"
    
    def _tratar_pagina_sem_anuncios(self, estado, pagina_atual, url_base):
        """Trata situação de página sem anúncios"""
        logging.warning(f"Nenhum anúncio encontrado na página {pagina_atual}. Salvando para análise.")
        
        with open(f"debug_page_{estado}_{pagina_atual}.html", "w", encoding="utf-8") as f:
            f.write(self.fazer_requisicao(f"{url_base}?o={pagina_atual}").text)
        
        time.sleep(random.uniform(*TEMPO_ESPERA_SEM_ANUNCIOS))
        return pagina_atual + 1
    
    def _processar_anuncios_da_pagina(self, links_anuncio, pagina_atual, nome_estado, total_processados):
        """Processa todos os anúncios de uma página"""
        for url_anuncio in tqdm(links_anuncio, desc=f"{nome_estado} - Página {pagina_atual}"):
            sucesso = self.processar_anuncio(url_anuncio)
            if sucesso:
                total_processados += 1
            
            if total_processados % 10 == 0:
                self.salvar_dados()
            
            time.sleep(random.uniform(*TEMPO_ESPERA_ENTRE_ANUNCIOS))
        
        return total_processados

    def rastrear(self, estados=None, max_paginas=100):
        """Executa o crawler para uma lista de estados"""
        if estados is None:
            estados = ['sp']  # Por padrão, apenas São Paulo
        
        total_geral = 0
        
        try:
            for estado in estados:
                if estado.lower() in self.estados:
                    anuncios_processados = self.rastrear_estado(estado.lower(), max_paginas)
                    total_geral += anuncios_processados
                    
                    # Pausa entre estados para reduzir a chance de detecção
                    tempo_espera = random.uniform(*TEMPO_ESPERA_PROXIMO_ESTADO)
                    logging.info(f"Concluído estado {self.estados.get(estado.lower())}. Aguardando {tempo_espera:.2f}s antes do próximo estado...")
                    time.sleep(tempo_espera)
                else:
                    logging.warning(f"Estado {estado} não reconhecido. Ignorando.")
        
        except KeyboardInterrupt:
            logging.info("Interrompido pelo usuário.")
        except Exception as e:
            logging.error(f"Erro durante o rastreamento: {e}", exc_info=True)
        finally:
            self.salvar_dados()
            logging.info(f"Rastreamento de todos estados finalizado. Total de anúncios processados: {total_geral}")

# Para executar o crawler
if __name__ == "__main__":
    try:
        crawler = OlxCrawler()
        estados = ['sp', 'rj', 'mg', 'ba', 'sc']
        crawler.rastrear(estados=estados, max_paginas=100)
    except Exception as e:
        logging.error(f"Erro ao executar crawler: {e}", exc_info=True)