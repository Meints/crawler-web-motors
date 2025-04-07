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