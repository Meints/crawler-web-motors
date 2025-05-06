# Relatório Parcial — Representação e Indexação de Dados (Fase 2)

## 🧩 Estrutura dos Dados

A base de dados utilizada foi extraída do site Webmotors, contendo informações hierárquicas sobre:

- **Marca** do veículo;
- **Modelo**;
- **Ano de fabricação**;
- **Faixa de preço** (quando disponível);
- **URL da referência**.

O arquivo `results_webmotors_full_content.json` foi a fonte primária de dados.

---

## 🧹 Etapas de Processamento

### 1. **Limpeza de Dados**
- Remoção de caracteres especiais, pontuações e números.
- Normalização de texto para minúsculas.
- Tokenização simples por espaços em branco.

### 2. **Análise Léxica**
- Aplicação de remoção de *stopwords* em português, com uma lista customizada para termos irrelevantes como "de", "o", "em", etc.

### 3. **Stemming**
- Implementado um stemmer simplificado baseado em regras manuais (ex: remoção de sufixos como "ções", "mente", "ico", etc.).

---

## 🧠 Representação e Indexação

### 📄 Índice Invertido

Criado um índice invertido no formato:

```json
"termo": ["doc_1", "doc_5", "doc_29"]
```

Com isso, é possível consultar rapidamente todos os documentos onde um determinado termo aparece.

### 📑 Metadados

Cada documento é representado por um identificador `doc_id` com os seguintes campos:

- Marca
- Modelo
- Ano
- Preço
- URL

Os metadados estão armazenados em `metadados_documentos.json`.

---

## 📊 Tamanho e Complexidade

- **Total de documentos indexados**: baseado na contagem de `doc_id`s.
- **Tamanho médio dos termos**: curto, pois aplicado stemming.
- **Espaço**: Arquivos JSON mantêm estrutura leve e legível.
- **Granularidade**: 1 documento por combinação única de marca + modelo + ano.

---

## 🗂 Próximos Passos

| Tarefa                                 | Responsável | Data Limite     |
|----------------------------------------|-------------|-----------------|
| Implementar sistema de consulta CLI    | Grupo       | DD/MM/2025      |
| Testar performance com termos comuns   | Grupo       | DD/MM/2025      |
| Comparar impacto de granularidade      | Grupo       | DD/MM/2025      |
| Documentar resultados e análise final  | Grupo       | DD/MM/2025      |
| Preparar apresentação final            | Grupo       | DD/MM/2025      |

---

## 📁 Arquivos Gerados

- `indice_invertido.json` → índice invertido com termos e documentos.
- `metadados_documentos.json` → detalhes de cada documento.

---

## ✅ Conclusão

Esta fase cumpriu com sucesso os requisitos da etapa de representação e indexação, utilizando técnicas de pré-processamento e estruturação textual adequadas para a natureza dos dados. O uso de arquivos JSON foi ideal para manter flexibilidade e independência de bancos relacionais (ACID).
