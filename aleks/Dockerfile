FROM python:3.9-slim

WORKDIR /app

# Copiar apenas o arquivo de requisitos primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código do crawler
COPY . .

# Criar diretório para dados
RUN mkdir -p data/html

# Comando para executar o crawler
CMD ["python", "crawler.py"]