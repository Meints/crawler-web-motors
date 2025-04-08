#!/usr/bin/env python3
# filepath: /home/aleks/projetos/recuperacao/crawler-web-motors/main.py
import os
import sys
import subprocess
import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
import time

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("CrawlerManager")

def run_crawler(crawler_name, crawler_path, max_pages=None, limit=None):
    """
    Executa um crawler específico como um processo separado
    
    Args:
        crawler_name: Nome do crawler (para logs)
        crawler_path: Caminho para o script Python do crawler
        max_pages: Número máximo de páginas (Aleks, Thiago e Pedro)
        limit: Número máximo de modelos (Cadu)
    """
    logger.info(f"Iniciando crawler: {crawler_name}")
    
    env = os.environ.copy()
    if max_pages:
        env["MAX_PAGES"] = str(max_pages)
    if limit:
        env["LIMIT"] = str(limit)
    
    try:
        process = subprocess.Popen(
            [sys.executable, crawler_path],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Captura a saída em tempo real
        for line in process.stdout:
            logger.info(f"[{crawler_name}] {line.strip()}")
        
        # Espera o processo terminar
        process.wait()
        
        # Captura erros
        stderr_output = process.stderr.read()
        if stderr_output:
            logger.error(f"[{crawler_name}] Erros: {stderr_output}")
            
        exit_code = process.returncode
        if exit_code == 0:
            logger.info(f"Crawler {crawler_name} concluído com sucesso")
        else:
            logger.error(f"Crawler {crawler_name} falhou com código de saída {exit_code}")
            
        return exit_code
        
    except Exception as e:
        logger.error(f"Erro ao executar crawler {crawler_name}: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description="Executa os crawlers do projeto")
    parser.add_argument("--crawler", choices=["aleks", "thiago", "cadu", "pedro", "all"], default="all",
                        help="Especifique qual crawler executar (default: all)")
    parser.add_argument("--sequential", action="store_true", 
                        help="Execute os crawlers sequencialmente em vez de paralelamente")
    parser.add_argument("--max-pages", type=int, default=10,
                        help="Número máximo de páginas a serem processadas (Aleks, Thiago e Pedro)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Número máximo de modelos a processar (Cadu)")
    args = parser.parse_args()
    
    # Caminhos para os scripts dos crawlers
    crawlers = {
        "aleks": "./aleks/crawler.py",
        "thiago": "./Thiago/crawler/WebMotors.py",
        "cadu": "./Cadu/Icarros.py",
        "pedro": "./Pedro/SemiNovos.py"
    }
    
    # Verificar se os arquivos existem
    for name, path in crawlers.items():
        if not os.path.exists(path):
            logger.error(f"Arquivo do crawler {name} não encontrado: {path}")
            return 1
    
    # Selecionar os crawlers a executar
    selected_crawlers = []
    if args.crawler == "all":
        selected_crawlers = list(crawlers.items())
    else:
        selected_crawlers = [(args.crawler, crawlers[args.crawler])]
    
    # Executar crawlers
    if args.sequential:
        logger.info("Executando crawlers sequencialmente")
        for name, path in selected_crawlers:
            max_pages_arg = args.max_pages if name in ["aleks", "thiago", "pedro"] else None
            limit_arg = args.limit if name == "cadu" else None
            exit_code = run_crawler(name, path, max_pages_arg, limit_arg)
            if exit_code != 0:
                logger.warning(f"Crawler {name} falhou, continuando com o próximo")
    else:
        logger.info("Executando crawlers em paralelo")
        with ThreadPoolExecutor(max_workers=len(selected_crawlers)) as executor:
            futures = []
            for name, path in selected_crawlers:
                max_pages_arg = args.max_pages if name in ["aleks", "thiago", "pedro"] else None
                limit_arg = args.limit if name == "cadu" else None
                futures.append(
                    executor.submit(run_crawler, name, path, max_pages_arg, limit_arg)
                )
            
            # Aguardar a conclusão de todos os crawlers
            for future in futures:
                future.result()
    
    logger.info("Todos os crawlers foram concluídos")
    return 0

if __name__ == "__main__":
    start_time = time.time()
    exit_code = main()
    elapsed_time = time.time() - start_time
    logger.info(f"Tempo total de execução: {elapsed_time:.2f} segundos")
    sys.exit(exit_code)