import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="QLF - Dashboard de Roteirização", layout="wide")

# ---------------- Funções Auxiliares ----------------
def ajustar_nome_cidade(df):
    df.columns = df.columns.str.strip()
    if "Município" in df.columns and "Cidade" not in df.columns:
        df = df.rename(columns={"Município": "Cidade"})
    return df

def processar_base_historica(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = ajustar_nome_cidade(df)
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df["AnoMes"] = df["Data"].dt.to_period("M").astype(str)
    cols_requeridas = ["Placa", "Tipo veículo", "Peso", "Cidade"]
    cols_existentes = [col for col in cols_requeridas if col in df.columns]
    df = df.dropna(subset=cols_existentes)
    df["Peso"] = pd.to_numeric(df["Peso"], errors="coerce")
    df = df.dropna(subset=["Peso"])
    return df

def encontrar_dias_parecidos(base, peso_ref, entregas_ref, cidades_ref, tolerancia=0.15):
    min_peso = peso_ref * (1 - tolerancia)
    max_peso = peso_ref * (1 + tolerancia)
    min_entregas = entregas_ref * (1 - tolerancia)
    max_entregas = entregas_ref * (1 + tolerancia)
    min_cidades = cidades_ref * (1 - tolerancia)
    max_cidades = cidades_ref * (1 + tolerancia)

    dias_agg = (
        base.groupby("Data")
        .agg(
            Peso_Total=("Peso", "sum"),
            Entregas=("Cidade", "count"),
            Cidades=("Cidade", pd.Series.nunique)
        )
        .reset_index()
    )

    dias_similares = dias_agg[
        (dias_agg["Peso_Total"].between(min_peso, max_peso)) &
        (dias_agg["Entregas"].between(min_entregas, max_entregas)) &
        (dias_agg["Cidades"].between(min_cidades, max_cidades))
    ]["Data"].tolist()

    return base[base["Data"].isin(dias_similares)]

# ---------------- Interface Principal ----------------
tab1, tab2 = st.tabs(["📊 Análise por Mês", "📥 Previsão com Volume Atual"])

with tab1:
    st.title("🚛 QLF - Análise de Placas por Mês")

    uploaded_file = st.file_uploader("📤 Envie sua planilha de viagens (Histórico)", type=["xlsx"], key="upload1")

    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            aba = xl.sheet_names[0]
            st.success(f"Aba utilizada: {aba}")
            df = xl.parse(aba)
        except Exception as e:
            st.error(f"Erro ao ler o arquivo: {e}")
            st.stop()

        df.columns = df.columns.str.strip()
        obrigatorias = {"Data", "Tipo veículo", "Placa"}

        if not obrigatorias.issubset(df.columns):
            st.error(f"❌ Colunas obrigatórias ausentes: {', '.join(obrigatorias - set(df.columns))}")
            st.stop()

        df = df.dropna(subset=["Data", "Tipo veículo", "Placa"])
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
        df = df.dropna(subset=["Data"])
        df["AnoMes"] = df["Data"].dt.to_period("M").astype(str)

        resumo = (
            df.groupby(["AnoMes", "Tipo veículo"])
              .agg(Placas_Distintas=("Placa", pd.Series.nunique))
              .reset_index()
        )

        st.sidebar.header("🔍 Filtros")
        meses = sorted(resumo["AnoMes"].unique())
        tipos = sorted(resumo["Tipo veículo"].unique())

        mes_sel = st.sidebar.selectbox("Filtrar por mês", options=["Todos"] + meses)
        tipo_sel = st.sidebar.multiselect("Filtrar por tipo de veículo", options=tipos, default=tipos)

        df_filtro = resumo.copy()
        if mes_sel != "Todos":
            df_filtro = df_filtro[df_filtro["AnoMes"] == mes_sel]
        if tipo_sel:
            df_filtro = df_filtro[df_filtro["Tipo veículo"].isin(tipo_sel)]

        st.subheader("📊 Resumo de Placas Distintas")
        st.dataframe(df_filtro, use_container_width=True)

        st.subheader("📈 Visualização")
        fig = px.bar(df_filtro, x="AnoMes", y="Placas_Distintas",
                     color="Tipo veículo", barmode="group",
                     labels={"Placas_Distintas": "Qtd. de Placas"},
                     title="Placas distintas por mês e tipo de veículo")
        st.plotly_chart(fig, use_container_width=True)

        if mes_sel != "Todos" and not df_filtro.empty:
            destaque = df_filtro.sort_values("Placas_Distintas", ascending=False)
            st.markdown("### 🏅 Destaques no mês selecionado")
            col1, col2 = st.columns(2)
            with col1:
                total = destaque["Placas_Distintas"].sum()
                st.metric("Total de veículos no mês", total)
            with col2:
                top = destaque.iloc[0]
                st.metric(f"Mais utilizado", f"{top['Tipo veículo']} ({top['Placas_Distintas']})")

with tab2:
    st.header("📥 Previsão de Veículos com Volume Diário")

    volume_file = st.file_uploader("📄 Envie a planilha de volume atual", type=["xlsx"], key="upload2")
    historico_file = st.file_uploader("📘 Envie a base histórica (PREVIA)", type=["xlsx"], key="upload3")

    if volume_file and historico_file:
        vol_df = pd.read_excel(volume_file)
        hist_df = pd.read_excel(historico_file, sheet_name=0)

        vol_df.columns = vol_df.columns.str.strip()
        hist_df.columns = hist_df.columns.str.strip()

        hist_df = ajustar_nome_cidade(hist_df)
        hist_df = processar_base_historica(hist_df)

        # Detecta automaticamente colunas relevantes na planilha de volume
        peso_col = next((col for col in vol_df.columns if "peso" in col.lower()), None)
        cidade_col = next((col for col in vol_df.columns if "cidade" in col.lower() or "município" in col.lower()), None)

        if not peso_col or not cidade_col:
            st.error("Colunas necessárias ('Peso' e 'Cidade' ou 'Município') não encontradas.")
            st.write("Colunas disponíveis:", vol_df.columns.tolist())
            st.stop()

        peso_total = pd.to_numeric(vol_df[peso_col], errors="coerce").sum()
        entregas_total = len(vol_df)
        cidades_total = vol_df[cidade_col].nunique()

        st.metric("Peso Total", f"{peso_total:,.0f} kg")
        st.metric("Entregas", entregas_total)
        st.metric("Cidades", cidades_total)

        st.markdown("---")
        st.subheader("🔍 Procurando dias similares no histórico...")

        dias_parecidos = encontrar_dias_parecidos(hist_df, peso_total, entregas_total, cidades_total)

        if dias_parecidos.empty:
            st.warning("Nenhum dia com características semelhantes foi encontrado.")
        else:
            resumo_pred = (
                dias_parecidos.groupby("Tipo veículo")
                .agg(Placas_Media=("Placa", pd.Series.nunique))
                .reset_index()
            )

            st.markdown("### 🚚 Estimativa de placas com base em dias similares:")
            st.dataframe(resumo_pred, use_container_width=True)

            total_placas = resumo_pred["Placas_Media"].sum()
            st.metric("Total estimado de veículos", f"{total_placas:.1f} placas")
