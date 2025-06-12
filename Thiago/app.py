# app.py ---------------------------------------------------------------
# UI Streamlit para o Sistema de Recuperação FIPE/WebMotors
#
# Requisitos extras:
#   pip install streamlit ir-measures pandas matplotlib
#
# Executar:
#   python -m streamlit run app.py
# ---------------------------------------------------------------------

import streamlit as st
from search import SearchEngine  # motor BM25 já implementado
import pandas as pd
import matplotlib.pyplot as plt
from tempfile import NamedTemporaryFile
from ir_measures import *  # P@10, MAP@10, nDCG@10
import ir_measures
import re

# ================== CONFIG & HELPERS =================================
ENGINE = SearchEngine()
st.set_page_config(page_title="Busca FIPE/WebMotors", page_icon="🚗", layout="wide")

def sanitize(text: str) -> str:
    """Remove espaços para obedecer ao formato TREC (qid/doc_id single‑token)."""
    return re.sub(r"\s+", "_", text)

# ===================== LAYOUT COM TABS ===============================
tab_busca, tab_eval = st.tabs(["🔎 Buscar", "📊 Avaliação"])

# =====================================================================
#  TAB 1 – BUSCA
# =====================================================================
with tab_busca:
    st.title("🔎 Sistema de Recuperação FIPE/WebMotors")

    with st.sidebar:
        st.header("⚙️ Configuração")
        topk_busca = st.slider("Quantos resultados?", 5, 50, 10)

    consulta = st.text_input("Digite sua consulta:", placeholder='ex.: "hilux 2022 diesel"')

    if consulta:
        resultados = ENGINE.search(consulta, topk=topk_busca)

        # ---------- ajuste extra: desempate por ano (se consulta termina com ano) ----------
        m = re.search(r"(19|20)\d{2}$", consulta.strip())
        if m:
            ano_query = int(m.group())
            for r in resultados:
                try:
                    diff = abs(int(r["ano"]) - ano_query)
                    r["score"] -= diff * 0.05  # penaliza 0,05 por ano de diferença
                except ValueError:
                    pass
        # recalcula ordem caso haja alteração
        resultados = sorted(resultados, key=lambda x: x["score"], reverse=True)

        if resultados:
            st.success(f"{len(resultados)} resultados encontrados")
            df_result = pd.DataFrame(resultados)
            df_result["score"] = df_result["score"].round(5)  # mostra 5 casas
            df_result = df_result[["score", "marca", "modelo", "ano", "preco", "url"]]
            df_result.columns = ["Score", "Marca", "Modelo", "Ano", "Preço", "Link"]
            st.table(df_result)

            with st.expander("Como interpretar o Score?", expanded=False):
                st.markdown(
                    """O **Score** vem da fórmula BM25. Documentos com a mesma combinação de termos
                    (marca, modelo, etc.) podem empatar. Neste caso aplicamos um pequeno ajuste que
                    favorece o **ano exato** quando a consulta termina com um ano."""
                )

            csv_bytes = df_result.to_csv(index=False).encode()
            st.download_button("⬇️ Baixar CSV", csv_bytes, file_name="resultados_busca.csv", mime="text/csv", use_container_width=True)
        else:
            st.warning("Nenhum resultado 😕")

# =====================================================================
#  TAB 2 – AVALIAÇÃO
# =====================================================================
with tab_eval:
    st.title("📊 Avaliação do Ranking")

    col_q, col_r = st.columns(2)
    queries_file = col_q.file_uploader("📄 queries.txt", type=["txt"])
    qrels_file   = col_r.file_uploader("📄 qrels.csv",  type=["csv"])
    topk_eval    = st.slider("Top-k a considerar", 5, 60, 10, key="topk_eval")
    st.caption(
        f"⬆️ **Top-k** define até onde o ranking será avaliado. "
        f"Com k = {topk_eval}, calculamos P@{topk_eval}, nDCG@{topk_eval} e MAP@{topk_eval}."
    )

    st.markdown("""**Formatos esperados**  
    • *queries.txt*: uma consulta por linha  
    • *qrels.csv*: `query,doc_id,rel`  (rel = 1 relevante, 0 irrelevante)  
    *doc_id* pode ser a URL que aparece na coluna **Link**.""")

    if st.button("▶️ Avaliar"):
        if not queries_file or not qrels_file:
            st.error("Envie **ambos** os arquivos primeiro.")
            st.stop()

        queries = [q.decode().strip() for q in queries_file.readlines() if q.strip()]
        if not queries:
            st.error("Arquivo de consultas vazio.")
            st.stop()

        # ------------------ run ---------------------------------------
        run_rows = []
        for q in queries:
            res = ENGINE.search(q, topk_eval)
            for rank, r in enumerate(res, 1):
                run_rows.append([sanitize(q), 0, sanitize(r["url"]), rank, r["score"], "bm25"])
        run_df = pd.DataFrame(run_rows, columns=["qid", "iter", "doc", "rank", "score", "tag"])
        st.write(f"Run gerado com **{len(run_df)} linhas**.")

        # ------------------ qrels -------------------------------------
        qrels_pd = pd.read_csv(qrels_file)
        qrels_pd["query"] = qrels_pd["query"].map(sanitize)
        qrels_pd["doc_id"] = qrels_pd["doc_id"].map(sanitize)
        qrels_pd.insert(1, "iter", 0)

        # ------------------ salvar tmp e avaliar ----------------------
        with NamedTemporaryFile(delete=False, suffix=".txt") as tq, NamedTemporaryFile(delete=False, suffix=".txt") as tr:
            qrels_pd.to_csv(tq.name, index=False, header=False, sep=" ")
            run_df.to_csv(tr.name, index=False, header=False, sep=" ")
            qrels_ir = ir_measures.read_trec_qrels(tq.name)
            run_ir   = ir_measures.read_trec_run(tr.name)
            mets     = [P@10, MAP@10, nDCG@10]
            res_aggr = ir_measures.calc_aggregate(mets, qrels_ir, run_ir)

        metr_df = pd.DataFrame({"Métrica": [m.__name__ for m in res_aggr], "Valor": [round(v, 4) for v in res_aggr.values()]})
        st.subheader("Resultados globais")
        st.dataframe(metr_df, use_container_width=True)

        # ------------------ resumo textual ----------------------------
        p_val, ndcg_val, ap_val = res_aggr[P@10], res_aggr[nDCG@10], res_aggr[MAP@10]
        def quality(m):
            return "(precisa de melhorias)" if m < 0.33 else "(razoável)" if m < 0.66 else "(muito bom!)"
        st.markdown(f"""
        - 🎯 **Precisão@{topk_eval}**: **{p_val:.1%}** dos primeiros {topk_eval} resultados são relevantes {quality(p_val)}  
        - 🏅 **nDCG@{topk_eval}**: **{ndcg_val:.2f}** {quality(ndcg_val)} – quanto mais próximo de 1, mais cedo aparecem os resultados corretos.  
        - 📈 **MAP@{topk_eval}**: **{ap_val:.2f}** indica a qualidade média percorrendo a lista.  
        """)

        # ------------------ gráfico -----------------------------------
        fig, ax = plt.subplots()
        ax.bar(metr_df["Métrica"], metr_df["Valor"])
        ax.set_ylim(0, 1)
        ax.set_ylabel("Valor")
        ax.set_title("Desempenho do Sistema")
        st.pyplot(fig, use_container_width=True)

        # ------------------ downloads ---------------------------------
        st.download_button("⬇️ Baixar run.csv", run_df.to_csv(index=False).encode(), file_name="run.csv", mime="text/csv", use_container_width=True)
        st.download_button("⬇️ Baixar métricas.csv", metr_df.to_csv(index=False).encode(), file_name="metricas.csv", mime="text/csv", use_container_width=True)
