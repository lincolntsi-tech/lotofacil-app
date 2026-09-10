import streamlit as st
import requests
import json
import time
from collections import Counter
import urllib3
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configuração da Página para Celular e Computador
st.set_page_config(
    page_title="Analisador Lotofácil",
    page_icon="🎱",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização visual (bolas coloridas)
st.markdown("""
<style>
    .dezena-box {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 38px;
        height: 38px;
        border-radius: 50%;
        background-color: #930089;
        color: white;
        font-weight: bold;
        font-size: 15px;
        margin: 3px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    .dezena-comp {
        background-color: #2E7D32 !important;
    }
</style>
""", unsafe_allow_html=True)

URL_BASE = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Referer": "https://loterias.caixa.gov.br/"
})

@st.cache_data(ttl=300)
def obter_dados_caixa():
    try:
        r = session.get(URL_BASE, timeout=12, verify=False)
        if r.status_code != 200:
            return None, "Erro de resposta da Caixa."
        atual = r.json()
        c_num = int(atual["numero"])
        
        amostra = []
        for n in range(c_num - 1, c_num - 11, -1):
            r_ant = session.get(f"{URL_BASE}/{n}", timeout=10, verify=False)
            if r_ant.status_code == 200:
                d = r_ant.json()
                amostra.append({
                    "numero": int(d["numero"]),
                    "data": d.get("dataApuracao", ""),
                    "dezenas": sorted([int(x) for x in d.get("listaDezenas", [])])
                })
            time.sleep(0.08)

        amostra.sort(key=lambda x: x["numero"])
        return {"atual": atual, "amostra": amostra}, None
    except Exception as e:
        return None, str(e)

def render_bolas(dezenas, classe="dezena-box"):
    html = "".join([f'<div class="{classe}">{d:02d}</div>' for d in dezenas])
    st.markdown(f'<div style="display:flex; flex-wrap:wrap; margin-bottom:10px;">{html}</div>', unsafe_allow_html=True)

st.title("🎱 Analisador Estratégico Lotofácil")
st.caption("Conexão oficial Caixa Econômica Federal")

col_btn, _ = st.columns([1, 3])
with col_btn:
    if st.button("🔄 Atualizar Análise", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

dados, erro = obter_dados_caixa()

if erro or not dados:
    st.error(f"Erro de conexão: {erro}")
    st.stop()

atual = dados["atual"]
amostra = dados["amostra"]
c_num = int(atual["numero"])
dezenas_atual = sorted([int(x) for x in atual.get("listaDezenas", [])])

st.markdown(f"### Concurso Atual: **{c_num}** ({atual.get('dataApuracao', '')})")
render_bolas(dezenas_atual)
st.markdown("---")

# Regra 2: Top 11
contagem = Counter()
recencia = {}
for dist, s in enumerate(reversed(amostra)):
    for dez in s["dezenas"]:
        contagem[dez] += 1
        if dez not in recencia:
            recencia[dez] = dist

ranking = sorted(range(1, 26), key=lambda d: (-contagem[d], recencia.get(d, 999), d))
top_11 = ranking[:11]

# Regra 3: Inícios
grupos = {1: [], 2: [], 3: [], "outros": []}
for s in amostra:
    d1 = s["dezenas"][0]
    if d1 in [1, 2, 3]:
        grupos[d1].append(s)
    else:
        grupos["outros"].append(s)

# Regra 4 e 5: Padrões
distrib = {}
padroes = {}
for ini in [1, 2, 3]:
    jogos = grupos[ini]
    tot = len(jogos)
    cnt = Counter()
    for j in jogos:
        for dez in j["dezenas"]:
            cnt[dez] += 1
    distrib[ini] = {"total": tot, "frequencias": cnt.most_common()}
    if jogos:
        seg = Counter([j["dezenas"][1] for j in jogos]).most_common(2)
        conj = [set(j["dezenas"]) for j in jogos]
        fix = sorted(list(set.intersection(*conj)))
        padroes[ini] = {"segunda": seg, "fixas": fix}

todos_sets = [set(s["dezenas"]) for s in amostra]
globais_100 = sorted(list(set.intersection(*todos_sets))) if todos_sets else []

# Regra 6: Streak
ultimo_ini = amostra[-1]["dezenas"][0]
streak = 0
for s in reversed(amostra):
    if s["dezenas"][0] == ultimo_ini:
        streak += 1
    else:
        break

transicoes = []
for i in range(len(amostra) - 1):
    a = amostra[i]["dezenas"][0]
    b = amostra[i + 1]["dezenas"][0]
    if a != b:
        transicoes.append((a, b))

# 15 Dezenas Finais
candidatas = [d for d, _ in distrib[ultimo_ini]["frequencias"] if d not in top_11]
if len(candidatas) < 4:
    candidatas += [d for d in ranking if d not in top_11 and d not in candidatas]
complementares = sorted(candidatas[:4])
jogo_final = sorted(top_11 + complementares)

st.subheader("🎯 Sugestão Estratégica: 15 Dezenas")
st.caption("11 Fixas (Roxo) + 4 Complementares Condicionais (Verde)")
html_final = "".join([
    f'<div class="dezena-box dezena-comp">{d:02d}</div>' if d in complementares else f'<div class="dezena-box">{d:02d}</div>'
    for d in jogo_final
])
st.markdown(f'<div style="display:flex; flex-wrap:wrap; margin-bottom:15px;">{html_final}</div>', unsafe_allow_html=True)
st.success(f"**Dezenas do volante:** {', '.join([f'{d:02d}' for d in jogo_final])}")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Top 11", "🎯 Inícios", "🔁 Streaks e Trocas", "📋 Concursos"])

with tab1:
    st.dataframe(pd.DataFrame([
        {"Dezena": f"{d:02d}", "Frequência": f"{contagem[d]}/10 jogos", "Recorrência": "Último jogo" if recencia[d] == 0 else f"Há {recencia[d]} jogo(s)"}
        for d in top_11
    ]), use_container_width=True, hide_index=True)

with tab2:
    for ini in [1, 2, 3]:
        info = distrib[ini]
        tot = info["total"]
        with st.expander(f"Início {ini} ({tot} de 10 jogos)", expanded=(ini == ultimo_ini)):
            if tot > 0:
                top_sec = [f"{d:02d} ({q}x)" for d, q in info["frequencias"] if d != ini][:5]
                st.write("**Mais sorteadas:**", ", ".join(top_sec))
                if ini in padroes and padroes[ini]["segunda"]:
                    st.write("**Segunda dezena comum:**", ", ".join([f"{d:02d} ({q}x)" for d, q in padroes[ini]["segunda"]]))
                fixas = padroes.get(ini, {}).get("fixas", [])
                st.write("**100% de presença:**", [f"{d:02d}" for d in fixas] if fixas else "Nenhuma")

with tab3:
    c1, c2 = st.columns(2)
    c1.metric("Último Início", f"Dezena {ultimo_ini}")
    c2.metric("Streak Atual", f"{streak} concurso(s)")
    if transicoes:
        for orig, dest in transicoes:
            st.write(f"• Início **{orig}** ➔ Mudou para Início **{dest}**")

with tab4:
    st.dataframe(pd.DataFrame([
        {"Concurso": s["numero"], "Data": s["data"], "Dezenas": " - ".join([f"{d:02d}" for d in s["dezenas"]])}
        for s in reversed(amostra)
    ]), use_container_width=True, hide_index=True)