FROM python:3.9-slim

WORKDIR /app

# Copiar apenas o arquivo de requisitos primeiro
COPY requirements.txt .

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código do crawler
COPY . .

# Criar diretório para dados
RUN mkdir -p data

# Comando para executar o crawler
CMD ["python", "crawler.py"]