import streamlit as st
import pandas as pd
import plotly.express as px
import io

st.set_page_config(page_title="QLF - Placas por Mês", layout="wide")
st.title("🚛 QLF - Análise de Placas por Mês")

uploaded_file = st.file_uploader("📤 Envie sua planilha de viagens", type=["xlsx"])

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

    # Agrupamento base
    resumo = (
        df.groupby(["AnoMes", "Tipo veículo"])
          .agg(Placas_Distintas=("Placa", pd.Series.nunique))
          .reset_index()
    )

    # Sidebar para filtros
    st.sidebar.header("🔍 Filtros")
    meses = sorted(resumo["AnoMes"].unique())
    tipos = sorted(resumo["Tipo veículo"].unique())

    mes_sel = st.sidebar.selectbox("Filtrar por mês", options=["Todos"] + meses)
    tipo_sel = st.sidebar.multiselect("Filtrar por tipo de veículo", options=tipos, default=tipos)

    # Aplicar filtros
    df_filtro = resumo.copy()
    if mes_sel != "Todos":
        df_filtro = df_filtro[df_filtro["AnoMes"] == mes_sel]
    if tipo_sel:
        df_filtro = df_filtro[df_filtro["Tipo veículo"].isin(tipo_sel)]

    st.subheader("📊 Resumo de Placas Distintas")
    st.dataframe(df_filtro, use_container_width=True)

    # Gráfico
    st.subheader("📈 Visualização")
    fig = px.bar(df_filtro, x="AnoMes", y="Placas_Distintas",
                 color="Tipo veículo", barmode="group",
                 labels={"Placas_Distintas": "Qtd. de Placas"},
                 title="Placas distintas por mês e tipo de veículo")
    st.plotly_chart(fig, use_container_width=True)

    # Destaques do mês
    if mes_sel != "Todos":
        destaque = df_filtro.sort_values("Placas_Distintas", ascending=False)
        st.markdown("### 🏅 Destaques no mês selecionado")
        col1, col2 = st.columns(2)
        with col1:
            total = destaque["Placas_Distintas"].sum()
            st.metric("Total de veículos no mês", total)
        with col2:
            top = destaque.iloc[0]
            st.metric(f"Mais utilizado", f"{top['Tipo veículo']} ({top['Placas_Distintas']})")

    # --- Cálculos com coluna Peso ---
    if "Peso" in df.columns:
        df["Peso"] = pd.to_numeric(df["Peso"], errors="coerce")
        df = df.dropna(subset=["Peso"])

        peso_agg = (
            df.groupby(["AnoMes", "Tipo veículo"])
              .agg(Peso_Total=("Peso", "sum"),
                   Placas_Distintas=("Placa", pd.Series.nunique))
              .reset_index()
        )

        if mes_sel != "Todos":
            peso_filtro = peso_agg[
                (peso_agg["AnoMes"] == mes_sel) &
                (peso_agg["Tipo veículo"].isin(tipo_sel))
            ]

            if not peso_filtro.empty:
                # --- Calculadora 1: Estimativa por tipo individual ---
                st.subheader("🧮 Estimativa de Placas por Tipo de Veículo")
                peso_input = st.number_input(
                    "Informe o peso que deseja transportar (em kg)",
                    min_value=0.0,
                    value=10000.0,
                    step=1000.0
                )

                for _, row in peso_filtro.iterrows():
                    placas_estimadas = (peso_input * row["Placas_Distintas"]) / row["Peso_Total"]
                    st.write(f"• **{row['Tipo veículo']}**: aprox. **{placas_estimadas:.1f} placas** para transportar {peso_input:,.0f} kg")

                # --- Calculadora 2: Alocação proporcional baseada em uso histórico ---
                st.subheader("📊 Alocação Inteligente com Base em Históricos")
                total_peso_input = st.number_input(
                    "Informe o volume total a transportar no mês (em kg)",
                    min_value=0.0,
                    value=100000.0,
                    step=10000.0,
                    key="peso_total_input"
                )

                peso_total_mes = peso_filtro["Peso_Total"].sum()
                peso_filtro = peso_filtro.copy()
                peso_filtro["Perc_uso"] = peso_filtro["Peso_Total"] / peso_total_mes
                peso_filtro["Peso_medio_por_placa"] = peso_filtro["Peso_Total"] / peso_filtro["Placas_Distintas"]

                st.markdown("### 🚚 Alocação sugerida:")
                for _, row in peso_filtro.iterrows():
                    peso_tipo = total_peso_input * row["Perc_uso"]
                    placas_est = peso_tipo / row["Peso_medio_por_placa"]
                    st.write(f"• **{row['Tipo veículo']}** → {placas_est:.1f} placas (transportando aprox. {peso_tipo:,.0f} kg)")

            else:
                st.warning("Sem dados de peso disponíveis para os filtros selecionados.")
        else:
            st.info("Selecione um mês específico para ativar as calculadoras.")
    else:
        st.warning("⚠️ A coluna 'Peso' (coluna L) não foi encontrada na planilha.")

    # Exportação
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_filtro.to_excel(writer, sheet_name="placas_filtradas", index=False)
    buffer.seek(0)

    st.download_button(
        label="⬇️ Baixar Excel filtrado",
        data=buffer,
        file_name="QLF_Placas_Filtrado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
