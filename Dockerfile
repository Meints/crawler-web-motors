FROM python:3.9-slim

WORKDIR /app

# Instalar pacotes necessários para o Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Instalar Chrome para o undetected-chromedriver
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Copiar todos os arquivos necessários
COPY requirements.txt .
COPY main.py .
COPY aleks/ ./aleks/
COPY Thiago/ ./Thiago/
COPY Cadu/ ./Cadu/
COPY Pedro/ ./Pedro/

# Instalar dependências
RUN pip install --no-cache-dir -r requirements.txt

# Criar diretórios para dados
RUN mkdir -p aleks/data aleks/data/html Thiago/data Cadu/data Pedro/data

# Comando para executar o main.py
CMD ["python", "main.py"]