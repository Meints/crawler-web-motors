# Análise e Indexação de Dados de Carros Seminovos

Este repositório contém dois scripts Python distintos para analisar e indexar dados de carros seminovos a partir de um arquivo JSON (`carros_seminovos_com_detalhes.json`). Cada script aborda a tarefa com diferentes técnicas de Processamento de Linguagem Natural (PLN) e estruturas de indexação.

## Script 1: `indexacao_simples_nltk.py`

### Descrição

Este script realiza uma indexação básica dos dados de carros seminovos, utilizando a biblioteca NLTK para pré-processamento de texto. O objetivo é criar um índice invertido e um arquivo de metadados para facilitar a busca por termos relevantes nos anúncios.

### Funcionalidades Principais

1.  **Carregamento de Dados JSON:** Lê o arquivo `carros_seminovos_com_detalhes.json`.
2.  **Pré-processamento de Texto com NLTK:**
    - Utiliza a lista de stopwords em português do NLTK.
    - Aplica o stemmer RSLP do NLTK para reduzir as palavras à sua raiz.
    - Remove pontuação e palavras curtas.
3.  **Construção do Índice Invertido:** Cria um mapeamento de cada termo para os IDs dos documentos (carros) onde ele aparece.
4.  **Criação do Mapa de Metadados:** Associa cada ID de documento às informações originais do carro (título, descrição, preço, anunciante, link, detalhes).
5.  **Salvamento dos Resultados:** Salva o índice invertido (`indice_invertido.json`) e os metadados (`metadados_documentos.json`) em arquivos JSON separados.

### Como Usar

1.  Certifique-se de ter a biblioteca NLTK instalada (`pip install nltk`).
2.  Execute o script: `python indexacao_simples_nltk.py`.
3.  Os arquivos `indice_invertido.json` e `metadados_documentos.json` serão gerados no mesmo diretório.

## Script 2: `indexacao_tfidf_busca.py`

### Descrição

Este script emprega técnicas mais avançadas de PLN para indexar e permitir a busca interativa nos dados de carros seminovos. Ele utiliza a vetorização TF-IDF para representar os textos dos anúncios e também constrói um índice invertido tradicional para a funcionalidade de busca.

### Funcionalidades Principais

1.  **Carregamento de Dados JSON e Criação de DataFrame:** Lê o arquivo JSON e o carrega em um DataFrame do pandas.
2.  **Pré-processamento de Texto com NLTK:**
    - Utiliza a lista de stopwords em português do NLTK.
    - Aplica o stemmer Snowball para português.
    - Remove caracteres especiais.
3.  **Vetorização com TF-IDF:** Converte os textos dos anúncios em vetores utilizando a técnica TF-IDF, que pondera a importância dos termos nos documentos.
4.  **Construção do Índice Invertido Tradicional:** Cria um mapeamento de termos para os índices dos documentos no DataFrame.
5.  **Exportação de Dados Limpos:** Salva uma versão limpa dos dados em `carros_seminovos_limpos.json`.
6.  **Busca Interativa (AND):** Permite ao usuário digitar termos de busca e retorna os anúncios que contêm todos os termos especificados.

### Como Usar

1.  Certifique-se de ter as bibliotecas pandas, NLTK e scikit-learn instaladas (`pip install pandas nltk scikit-learn`).
2.  Execute o script: `python indexacao_tfidf_busca.py`.
3.  Após a indexação, o script entrará em um modo de busca interativa. Digite os termos que deseja buscar (separados por espaço) e pressione Enter. Digite `sair` para encerrar a busca.
4.  O arquivo `carros_seminovos_limpos.json` também será gerado.

## Observações

- Ambos os scripts assumem que o arquivo de dados `carros_seminovos_com_detalhes.json` está localizado em um subdiretório chamado `data/`. Certifique-se de criar este diretório e mover o arquivo JSON para lá, ou ajuste o caminho do arquivo nos scripts conforme necessário.
- O Script 2 (`indexacao_tfidf_busca.py`) oferece uma abordagem mais sofisticada para a representação de texto (TF-IDF) e uma funcionalidade de busca interativa, enquanto o Script 1 (`indexacao_simples_nltk.py`) foca em uma indexação mais direta utilizando stemming básico.
- Os arquivos de saída do Script 1 são `indice_invertido.json` e `metadados_documentos.json`.
- O Script 2 gera o índice invertido na memória para a busca interativa e também salva os dados limpos em `carros_seminovos_limpos.json`.

Escolha o script que melhor se adapta às suas necessidades de análise e busca nos dados de carros seminovos. O Script 2 pode fornecer resultados de busca mais relevantes devido ao uso do TF-IDF, enquanto o Script 1 é mais simples e direto para uma indexação básica.
