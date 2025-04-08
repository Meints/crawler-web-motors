# USANDO DOCKER

Este projeto pode ser facilmente executado usando Docker, sem necessidade de configurar ambientes Python locais.

## Pré-requisitos
- Docker
- Docker Compose

## Executando os crawlers com Docker

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/crawler-web-motors.git
cd crawler-web-motors

# 2. Construa e execute os containers
docker-compose build
docker-compose up -d

# 3. Para acompanhar os logs do crawler de Aleks
docker-compose logs -f aleks-crawler

# 4. Para acompanhar os logs do crawler de Thiago
docker-compose logs -f thiago-crawler

# 5. Para parar os containers
docker-compose down
```

# Instruções para uso unificado

Além de poder executar cada crawler individualmente, você pode executar todos eles simultaneamente ou sequencialmente.

## Execução manual (fora do Docker)

```bash
# 1. Instalar todas as dependências
pip install -r requirements.txt

# 2. Executar todos os crawlers simultaneamente
python main.py

# 3. Executar todos os crawlers sequencialmente
python main.py --sequential

# 4. Executar apenas um crawler específico
python main.py --crawler aleks
python main.py --crawler thiago
python main.py --crawler cadu

# 5. Definir limites de coleta
python main.py --max-pages 20 --limit 15

# Executar todos os crawlers em um único container
docker-compose up all-crawlers

# OU executar cada crawler em seu próprio container
docker-compose up