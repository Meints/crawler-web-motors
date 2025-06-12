## Descrição do Código de Indexação de Dados de Carros

Este script Python tem como objetivo processar um arquivo JSON contendo informações sobre carros e criar um índice invertido para facilitar a busca por termos relevantes nos dados. Além do índice invertido, ele também gera um arquivo de metadados que mapeia identificadores únicos para cada registro de carro com suas informações completas.

**Funcionalidades Principais:**

1.  **Carregamento de Dados JSON:**

    - Lê um arquivo JSON chamado `carros_localiza_completo.json`.
    - Inclui tratamento de erros caso o arquivo não seja encontrado.

2.  **Pré-processamento de Texto:**

    - **`clean_text(text)`:** Realiza a limpeza e normalização do texto extraído de cada registro de carro:
      - Converte o texto para minúsculas.
      - Remove caracteres de pontuação.
      - Remove números.
      - Divide o texto em palavras (tokens).
      - Filtra os tokens, removendo palavras presentes em uma lista de stopwords manual e palavras com menos de 3 caracteres.
      - Aplica um stemming simples para reduzir as palavras à sua raiz.
    - **`simple_stem(word)`:** Uma função de stemming simplificada para a língua portuguesa, removendo sufixos comuns.
    - **`stop_words`:** Uma lista predefinida de palavras comuns em português (stopwords) e alguns termos específicos encontrados nos dados de carros (`preços`, `disponíveis`, `ano`, `modelo`, `km`, `r$`, `|`, `flex`, `1.0`).
    - **`is_valid_token(token)`:** Uma função para verificar se um token é válido (comprimento maior que 2 e não é uma stopword).

3.  **Construção do Índice Invertido:**

    - Itera sobre cada objeto (carro) na lista carregada do arquivo JSON.
    - Extrai informações relevantes como marca, modelo, km, ano, câmbio, preço (de e atual), local e link.
    - Combina essas informações em um único texto para cada carro.
    - Aplica as funções de limpeza (`clean_text`) para obter os termos relevantes.
    - Cria um índice invertido (`inverted_index`) onde cada termo único mapeia para um conjunto de IDs de documentos (carros) onde esse termo aparece.

4.  **Criação do Mapa de Metadados dos Documentos:**

    - Mantém um dicionário (`doc_id_map`) que associa um ID único (`doc_id`) a todas as informações originais de cada carro. Isso permite recuperar os detalhes completos de um carro a partir de seu ID no índice invertido.

5.  **Salvamento dos Resultados:**
    - Salva o `inverted_index` em um arquivo JSON chamado `indice_invertido_localiza_simples.json`. Os conjuntos de IDs de documentos são convertidos para listas ordenadas antes de serem salvos.
    - Salva o `doc_id_map` em um arquivo JSON chamado `metadados_documentos_localiza_simples.json`.
    - Imprime uma mensagem de sucesso indicando os arquivos gerados.

**Em resumo, este script processa dados de carros em formato JSON, realiza um pré-processamento básico de texto (limpeza, remoção de stopwords e stemming), e constrói um índice invertido para otimizar a busca por informações dentro desses dados. Ele também preserva as informações completas de cada carro em um arquivo de metadados.**
