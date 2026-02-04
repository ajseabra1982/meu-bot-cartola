import streamlit as st
import pandas as pd
import requests
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Cartola Pro: Scaler Automático", layout="wide", page_icon="🏆")

# Estilo para as métricas e cards
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); border: 1px solid #e0e0e0; }
    .status-provavel { color: green; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÕES DE DADOS
@st.cache_data(ttl=3600)
def carregar_dados_completos():
    try:
        # Dados Atletas
        r_mercado = requests.get("https://api.cartola.globo.com/atletas/mercado", timeout=10).json()
        # Dados Partidas
        r_partidas = requests.get("https://api.cartola.globo.com/partidas", timeout=10).json()
        
        clubes_map = {int(id): c['nome'] for id, c in r_mercado['clubes'].items()}
        posicoes_map = {1: 'Goleiro', 2: 'Lateral', 3: 'Zagueiro', 4: 'Meia', 5: 'Atacante', 6: 'Técnico'}
        status_map = {7: 'Provável', 2: 'Dúvida', 5: 'Contundido', 6: 'Suspenso', 3: 'Nulo'}
        
        df = pd.DataFrame(r_mercado['atletas'])
        df['posicao'] = df['posicao_id'].map(posicoes_map)
        df['status'] = df['status_id'].map(status_map)
        df['clube'] = df['clube_id'].map(clubes_map)
        
        # Métrica de Eficiência
        df['eficiencia'] = df.apply(lambda x: x['media_num'] / x['preco_num'] if x['preco_num'] > 0 else 0, axis=1)
        
        return df, r_partidas['partidas'], clubes_map
    except Exception as e:
        st.error(f"Erro ao conectar com a API: {e}")
        return pd.DataFrame(), [], {}

# 3. LÓGICA DE ESCALAÇÃO AUTOMÁTICA
def gerar_time_ideal(df_base, orçamento):
    # Filtra apenas quem vai jogar
    df_provaveis = df_base[df_base['status'] == 'Provável'].copy()
    
    time_escalado = []
    custo_total = 0
    
    # Definição de esquema 4-3-3 (1 GOL, 2 LAT, 2 ZAG, 3 MEI, 3 ATA)
    esquema = {'Goleiro': 1, 'Lateral': 2, 'Zagueiro': 2, 'Meia': 3, 'Atacante': 3}
    
    for pos, qtd in esquema.items():
        # Busca os melhores da posição por média técnica que caibam no preço médio
        candidatos = df_provaveis[df_provaveis['posicao'] == pos].sort_values(by='media_num', ascending=False)
        
        selecionados = candidatos.head(qtd)
        time_escalado.append(selecionados)
        custo_total += selecionados['preco_num'].sum()
        
    df_time = pd.concat(time_escalado)
    return df_time, custo_total

# --- INÍCIO DA INTERFACE ---
st.title("🏆 Cartola Pro Scaler")
st.markdown("Análise estatística e escalação automática baseada em dados reais.")

df_atletas, partidas, mapa_clubes = carregar_dados_completos()

if not df_atletas.empty:
    # --- BARRA LATERAL ---
    st.sidebar.header("🎯 Filtros e Orçamento")
    orcamento_max = st.sidebar.number_input("Seu Patrimônio (C$)", min_value=50.0, max_value=300.0, value=120.0)
    min_jogos = st.sidebar.slider("Mínimo de Jogos no Ano", 0, 38, 3)
    
    df_filtrado = df_atletas[df_atletas['jogos_num'] >= min_jogos].copy()

    # --- ABA 1: ANÁLISE DE CONFRONTOS ---
    st.subheader("🛡️ Defesas Frágeis & Onde Atacar")
    fragilidade = df_atletas.groupby('clube')['media_num'].mean().sort_values().head(5)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write("**Times em Baixa (Alvos):**")
        st.dataframe(fragilidade)
    with c2:
        st.write("**Análise de Jogos:**")
        for p in partidas:
            casa, fora = mapa_clubes.get(p['clube_casa_id']), mapa_clubes.get(p['clube_visitante_id'])
            if fora in fragilidade.index:
                st.success(f"🔥 **{casa}** tem favoritismo contra a defesa do {fora}")
            elif casa in fragilidade.index:
                st.success(f"🔥 **{fora}** tem favoritismo contra a defesa do {casa}")

    st.divider()

    # --- ABA 2: ESCALAÇÃO AUTOMÁTICA ---
    st.subheader("🤖 Sugestão de Time (Esquema 4-3-3)")
    if st.button("🚀 GERAR TIME IDEAL"):
        time_sugerido, custo = gerar_time_ideal(df_filtrado, orcamento_max)
        
        if custo > orcamento_max:
            st.warning(f"O time sugerido (C$ {custo:.2f}) ultrapassa seu patrimônio. Tente aumentar o patrimônio na barra lateral.")
        
        st.table(time_sugerido[['apelido', 'posicao', 'clube', 'media_num', 'preco_num']])
        st.metric("Custo Total da Sugestão", f"C$ {custo:.2f}")
        st.info("O algoritmo prioriza Média Técnica entre os jogadores Prováveis.")

    st.divider()

    # --- ABA 3: MANUAL DE USO ---
    with st.expander("📖 MANUAL DO ANALISTA (CLIQUE PARA ABRIR)"):
        st.markdown("""
        ### Como mitar usando este bot:
        1. **Patrimônio:** Insira quanto você tem disponível. O bot tentará buscar os melhores que caibam no bolso.
        2. **Alvos da Rodada:** Olhe a seção de 'Defesas Frágeis'. Jogadores que enfrentam esses times têm maior chance de bônus de gol e assistência.
        3. **Mínimo de Jogos:** Defina pelo menos **3 ou 5 jogos**. Isso evita escalar um jogador que foi bem em apenas uma rodada por sorte.
        4. **Eficiência:** Se um jogador tem eficiência alta (>0.70), ele é um 'Bom e Barato'. Ótimo para ganhar cartoletas.
        5. **Status:** O bot foca apenas em jogadores **Prováveis** para evitar que você escale alguém que não vai a campo.
        """)

    # --- LISTA GERAL ---
    st.subheader("📋 Base de Dados Completa")
    st.dataframe(df_filtrado.sort_values(by='media_num', ascending=False), use_container_width=True)

    # Exportar
    csv = df_filtrado.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Dados (CSV)", csv, "dados_cartola.csv", "text/csv")

else:
    st.warning("Não foi possível carregar os dados. Verifique se o mercado está aberto.")