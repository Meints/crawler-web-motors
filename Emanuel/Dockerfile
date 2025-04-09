FROM python:3.9-slim

WORKDIR /app

# Copiar apenas o arquivo de requisitos primeiro
COPY requirements.txt .

# Instalar dependências
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    && rm -rf /var/lib/apt/lists/*

# Configura o Selenium para usar o Chrome headless no container
ENV PATH="/usr/lib/chromium/:${PATH}"
ENV CHROME_BIN="/usr/bin/chromium"
ENV CHROMEDRIVER_PATH="/usr/lib/chromium/chromedriver"

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código do crawler
COPY . .

# Criar diretório para dados
RUN mkdir -p data

# Comando para executar o crawler
CMD ["python", "crawler.py"]