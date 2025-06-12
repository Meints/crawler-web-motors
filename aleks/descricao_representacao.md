# Descrição da Representação dos Dados

## 1. Coleta e Estrutura dos Dados

Os dados foram coletados automaticamente a partir de anúncios de veículos na OLX, utilizando um crawler próprio. Cada anúncio é armazenado como um dicionário (objeto JSON) contendo, no mínimo, os seguintes campos:
- `id`: identificador único do anúncio
- `marca`: marca do veículo
- `modelo`: modelo do veículo
- `estado`: estado de localização do anúncio
- `preco`: valor anunciado

Esses registros são salvos em um arquivo `anuncios.json`, que contém uma lista de todos os anúncios coletados.

---

## 2. Limpeza e Pré-processamento

Antes da indexação, os dados passam por um processo de limpeza e transformação:
- **Padronização textual:** Todos os textos são convertidos para minúsculas e têm a pontuação removida.
- **Remoção de campos vazios:** Anúncios sem os campos essenciais são ignorados no processo de indexação.
- **Tokenização:** Os textos são divididos em palavras (tokens).
- **Remoção de stopwords:** Palavras comuns do português, que não agregam significado à busca (ex: "de", "o", "e"), são removidas.
- **Stemming:** As palavras são reduzidas ao seu radical, facilitando a busca por diferentes variações de um mesmo termo.

---

## 3. Representação e Indexação

A representação dos dados para busca eficiente é feita por meio de um **índice invertido**. Esse índice é uma estrutura que mapeia cada termo relevante para a lista de anúncios em que ele aparece.

### Granularidade
O índice pode ser construído de duas formas:
- **Por campo:** Cada termo é indexado junto ao nome do campo (ex: `marca:honda`, `modelo:civic`), permitindo buscas mais refinadas.
- **Por anúncio:** Todos os campos textuais são combinados e indexados juntos, facilitando buscas gerais.

### Chunk/Bucket
Para otimizar o uso de memória e o desempenho, o processamento é feito em blocos (chunks) de 100 anúncios por vez. Esse parâmetro pode ser ajustado conforme a necessidade.

### Formato do Índice Invertido
O índice é salvo em formato JSON, por exemplo:
```json
{
  "marca:honda": ["id1", "id2"],
  "modelo:civic": ["id1"],
  "estado:sp": ["id1", "id3"],
  "preco:50000": ["id2"]
}
```
Isso permite buscas rápidas por qualquer termo ou combinação de termos.

---

## 4. Métricas e Hiperparâmetros

Durante o processamento, são registradas as seguintes métricas:
- Tempo total de processamento
- Uso de memória
- Tamanho do índice invertido gerado
- Granularidade e tamanho do chunk utilizados
- Total de termos indexados
- Total de anúncios processados

Essas informações são salvas em um arquivo `metricas_processamento.json` para facilitar a análise e ajustes futuros.

---

## 5. Justificativa da Representação

A escolha do índice invertido se deve à sua eficiência para buscas textuais, especialmente em grandes volumes de dados. O uso de granularidade por campo permite consultas mais precisas, enquanto o processamento em chunks garante escalabilidade e baixo consumo de memória.

O formato JSON foi escolhido por ser leve, flexível e de fácil integração com outras ferramentas de análise e visualização. 