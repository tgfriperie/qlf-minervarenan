import streamlit as st

st.title("🚚 Calculadora de Frota - QLF Minerva Foods")

st.markdown("---")

# ---------------- CALCULADORA COMPLETA ----------------
st.header("1️⃣ Calculadora Completa (configurável)")

volume = st.number_input("Volume do dia (em kg)", min_value=0, value=30000, step=500)

st.subheader("🔧 Frota disponível (você pode alterar)")
v_34 = st.number_input("Caminhão 3/4 - Quantidade", value=9)
v_34_cap = st.number_input("Caminhão 3/4 - Capacidade (kg)", value=3500)

v_semi = st.number_input("Semi Leve - Quantidade", value=6)
v_semi_cap = st.number_input("Semi Leve - Capacidade (kg)", value=1500)

v_vuc = st.number_input("VUC - Quantidade", value=2)
v_vuc_cap = st.number_input("VUC - Capacidade (kg)", value=2000)

v_fiorino = st.number_input("Fiorino - Quantidade", value=2)
v_fiorino_cap = st.number_input("Fiorino - Capacidade (kg)", value=600)

st.markdown("")

# Função para alocar
def alocar_veiculos(qtd_disp, capacidade, restante):
    usados = 0
    for _ in range(qtd_disp):
        if restante <= 0:
            break
        restante -= capacidade
        usados += 1
    return usados, max(restante, 0)

restante = volume
usados = {}

usados["3/4"], restante = alocar_veiculos(v_34, v_34_cap, restante)
usados["Semi Leve"], restante = alocar_veiculos(v_semi, v_semi_cap, restante)
usados["VUC"], restante = alocar_veiculos(v_vuc, v_vuc_cap, restante)
usados["Fiorino"], restante = alocar_veiculos(v_fiorino, v_fiorino_cap, restante)

st.subheader("📊 Resultado da Alocação")
for tipo, qtd in usados.items():
    st.write(f"{tipo}: {qtd} veículo(s) usado(s)")

if restante > 0:
    st.error(f"⚠️ Sobrou {restante} kg sem alocar")
else:
    st.success("✅ Volume alocado com sucesso!")

st.markdown("---")

# ---------------- CALCULADORA SIMPLIFICADA ----------------
st.header("2️⃣ Calculadora Rápida com Médias Fixas")

vol_input = st.number_input("Informe o volume do dia (kg)", min_value=0, value=20000, step=500, key="simples")

# Médias fixas da frota atual
medias = {
    "3/4": {"quantidade": 9, "capacidade": 3500},
    "Semi Leve": {"quantidade": 6, "capacidade": 1500},
    "VUC": {"quantidade": 2, "capacidade": 2000},
    "Fiorino": {"quantidade": 2, "capacidade": 600}
}

restante_simples = vol_input
usados_simples = {}

# Alocação com médias fixas
for tipo, info in medias.items():
    usados_simples[tipo], restante_simples = alocar_veiculos(
        info["quantidade"], info["capacidade"], restante_simples
    )

# Exibição dos resultados
st.subheader("📊 Resultado com Médias Fixas")
st.markdown(f"**🔢 Volume informado:** {vol_input} kg")

for tipo, qtd in usados_simples.items():
    st.markdown(f"- **{tipo}**: {qtd} veículo(s) usado(s)")

if restante_simples > 0:
    st.error(f"⚠️ Ainda faltam **{restante_simples} kg** sem veículo disponível.")
else:
    st.success("✅ Volume atendido com a frota média atual!")
