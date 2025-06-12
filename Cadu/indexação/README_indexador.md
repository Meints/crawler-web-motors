# 🔍 Indexador de Dados - Projeto de Indexação e Recuperação

Este projeto realiza a **extração, pré-processamento e indexação invertida** de dados textuais de um arquivo JSON contendo informações sobre veículos (baseado em dados do iCarros).

---

## 📁 Estrutura de Pastas

```
indexação/
├── indexador.py
├── setup_nltk.py
├── requirements.txt
└── ../data/
    ├── icarros_dados_completos.json
    └── indice_invertido.json (gerado ao final)
```

---

## ⚙️ Requisitos

Antes de tudo, instale os pacotes necessários:

```bash
pip install -r requirements.txt
```

---

## 📦 Setup Inicial

É necessário baixar os recursos do NLTK antes da execução:

```bash
python setup_nltk.py
```

---

## 🚀 Executando o Indexador

Para rodar o indexador e gerar o índice invertido:

```bash
python indexador.py
```

### Saídas:
- Tempo de execução
- Tamanho do índice (número de termos únicos)
- Uso estimado de memória
- Arquivo `indice_invertido.json` com os dados processados

---

## 🧠 O que o script faz?

### 1. **Pré-processamento**
- Converte texto para minúsculas
- Remove pontuações
- Tokeniza as palavras
- Remove *stopwords*
- Aplica *stemming* com `RSLPStemmer`

### 2. **Extração**
- Lê o JSON `icarros_dados_completos.json`
- Combina modelo, versão e ficha técnica
- Transforma o conteúdo em uma lista de tokens processados por documento

### 3. **Indexação**
- Cria um **índice invertido** no formato `{termo: [ids de documentos]}`

---

## 💾 Resultado

O índice invertido será salvo como:

```
../data/indice_invertido.json
```

---

## 📝 Observação

Certifique-se de que o arquivo `icarros_dados_completos.json` está presente no diretório `data/` **um nível acima** da pasta `indexação/`, conforme esperado no caminho relativo do script.

---

## ✅ Exemplo de uso

```bash
python indexador.py
```

Saída esperada:

```
🚀 Iniciando indexação...
Diretório atual: /caminho/para/indexação
⏱ Tempo de indexação: 1.34 segundos
📦 Tamanho do índice (número de termos): 978
💾 Memória estimada do índice: 84128 bytes
✅ Índice invertido salvo em 'data/indice_invertido.json'
```

---

## 📚 Referências
- [NLTK Documentation](https://www.nltk.org/)
- [RSLP Stemmer](https://www.nltk.org/howto/stem.html)

---

Desenvolvido para fins acadêmicos na disciplina de Representação e Recuperação da Informação.
