FROM python:3.9-slim

WORKDIR /app

# Copiar requisitos e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código do crawler
COPY aleks/ .

# Criar diretório de dados
RUN mkdir -p data

# Comando para executar o crawler
CMD ["python", "crawler.py"]
