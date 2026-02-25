import streamlit as st
import pandas as pd
import requests
import io

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Cartola Pro: Scaler Inteligente", layout="wide", page_icon="🏆")

@st.cache_data(ttl=3600)
def carregar_dados_completos():
    try:
        r_mercado = requests.get("https://api.cartola.globo.com/atletas/mercado", timeout=10).json()
        r_partidas = requests.get("https://api.cartola.globo.com/partidas", timeout=10).json()
        
        clubes_map = {int(id): c['nome'] for id, c in r_mercado['clubes'].items()}
        posicoes_map = {1: 'Goleiro', 2: 'Lateral', 3: 'Zagueiro', 4: 'Meia', 5: 'Atacante', 6: 'Técnico'}
        status_map = {7: 'Provável', 2: 'Dúvida', 5: 'Contundido', 6: 'Suspenso', 3: 'Nulo'}
        
        df = pd.DataFrame(r_mercado['atletas'])
        df['posicao'] = df['posicao_id'].map(posicoes_map)
        df['status'] = df['status_id'].map(status_map)
        df['clube'] = df['clube_id'].map(clubes_map)
        
        # Métrica de Eficiência: Pontos por Cartoleta
        df['eficiencia'] = df.apply(lambda x: x['media_num'] / x['preco_num'] if x['preco_num'] > 0 else 0, axis=1)
        
        return df, r_partidas['partidas'], clubes_map
    except:
        return pd.DataFrame(), [], {}

# 2. LÓGICA DE ESCALAÇÃO OTIMIZADA
def montar_esquadrao(df_base, criterio='media_num', orcamento=100.0):
    df_provaveis = df_base[df_base['status'] == 'Provável'].copy()
    esquema = {'Goleiro': 1, 'Lateral': 2, 'Zagueiro': 2, 'Meia': 3, 'Atacante': 3}
    
    time_escalado = []
    # Definimos um teto de preço médio por jogador para não estourar
    preco_medio_max = orcamento / 11 
    
    for pos, qtd in esquema.items():
        # Filtra por posição e ordena pelo critério (Média ou Eficiência)
        candidatos = df_provaveis[df_provaveis['posicao'] == pos].sort_values(by=criterio, ascending=False)
        
        # Tenta pegar jogadores que não fiquem absurdamente caros
        selecionados = candidatos[candidatos['preco_num'] <= (preco_medio_max * 1.5)].head(qtd)
        time_escalado.append(selecionados)
        
    df_resultado = pd.concat(time_escalado)
    return df_resultado, df_resultado['preco_num'].sum()

# --- INTERFACE ---
st.title("🏆 Cartola Pro Scaler - 3ª Rodada")

df_atletas, partidas, mapa_clubes = carregar_dados_completos()

if not df_atletas.empty:
    st.sidebar.header("🎯 Configurações")
    patrimonio = st.sidebar.number_input("Seu Patrimônio Atual (C$)", value=100.0, step=1.0)
    
    # --- SEÇÃO DE SUGESTÕES ---
    st.subheader(f"🤖 Sugestões para Patrimônio de C$ {patrimonio}")
    
    tab1, tab2 = st.tabs(["💰 Time Bom e Barato (Foco em Custo-Benefício)", "⭐ Time Elite (Foco em Pontuação)"])
    
    with tab1:
        st.info("Este time prioriza jogadores com alta Eficiência (pontuam bem custando pouco). Ideal para valorização.")
        time_bb, custo_bb = montar_esquadrao(df_atletas, criterio='eficiencia', orcamento=patrimonio)
        st.table(time_bb[['apelido', 'posicao', 'clube', 'media_num', 'preco_num', 'eficiencia']])
        st.metric("Custo Total", f"C$ {custo_bb:.2f}", delta=f"{patrimonio - custo_bb:.2f} sobra")

    with tab2:
        st.info("Este time busca as maiores médias técnicas, respeitando o limite de preço médio.")
        time_el, custo_el = montar_esquadrao(df_atletas, criterio='media_num', orcamento=patrimonio)
        st.table(time_el[['apelido', 'posicao', 'clube', 'media_num', 'preco_num']])
        st.metric("Custo Total", f"C$ {custo_el:.2f}", delta=f"{patrimonio - custo_el:.2f} sobra")
        if custo_el > patrimonio:
            st.error("⚠️ Atenção: Este time ultrapassou seu orçamento. Use a opção 'Bom e Barato'.")

    # --- ANÁLISE DE CONFRONTOS ---
    st.divider()
    st.subheader("🛡️ Defesas frágeis da rodada")
    # Calcula quem mais cede pontos (adversários dos times que pontuam pouco)
    fragilidade = df_atletas.groupby('clube')['media_num'].mean().sort_values().head(5)
    
    cols = st.columns(len(partidas[:5])) # Mostra os primeiros 5 jogos
    for i, p in enumerate(partidas[:5]):
        casa = mapa_clubes.get(p['clube_casa_id'])
        fora = mapa_clubes.get(p['clube_visitante_id'])
        with cols[i]:
            if fora in fragilidade.index:
                st.success(f"**{casa}** 🏠\n(Alvo: {fora})")
            elif casa in fragilidade.index:
                st.success(f"**{fora}** ✈️\n(Alvo: {casa})")
            else:
                st.write(f"{casa} x {fora}")

    # --- MANUAL ---
    with st.expander("📖 Manual para a 3ª Rodada"):
        st.write("""
        1. **Valorização:** Na 3ª rodada, o sistema de valorização ainda está se estabilizando. O 'Time Bom e Barato' é o mais seguro para aumentar seu patrimônio.
        2. **Eficiência:** Foque em jogadores com eficiência acima de 0.60.
        3. **Saldo de Gol (SG):** Para a defesa, priorize times mandantes que enfrentam os 'Alvos' listados acima.
        """)

else:
    st.error("Erro ao carregar os dados. O mercado pode estar fechado.")