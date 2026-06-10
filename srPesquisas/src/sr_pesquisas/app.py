import streamlit as st
import time
from sr_pesquisas.agents.pipeline import research_graph
from sr_pesquisas.database.engine import init_db

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="srPesquisas | IA Academic Scout",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- ESTILIZAÇÃO TUI (Terminal User Interface) ---
st.markdown("""
    <style>
    /* Importando fonte monoespaçada */
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');

    /* Reset de cores para tema Dark/Terminal */
    :root {
        --terminal-green: #00FF00;
        --terminal-bg: #0A0A0A;
        --terminal-amber: #FFB000;
    }

    .stApp {
        background-color: var(--terminal-bg);
        color: var(--terminal-green);
        font-family: 'JetBrains Mono', monospace;
    }

    /* Estilização de Headers */
    h1, h2, h3 {
        color: var(--terminal-green) !important;
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-bottom: 1px solid var(--terminal-green);
        padding-bottom: 10px;
    }

    /* Input Fields */
    .stTextInput > div > div > input {
        background-color: #1A1A1A !important;
        color: var(--terminal-green) !important;
        border: 1px solid var(--terminal-green) !important;
        border-radius: 0px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Buttons */
    .stButton > button {
        background-color: transparent !important;
        color: var(--terminal-green) !important;
        border: 1px solid var(--terminal-green) !important;
        border-radius: 0px !important;
        width: 100%;
        text-transform: uppercase;
        font-weight: bold;
        transition: 0.3s;
    }

    .stButton > button:hover {
        background-color: var(--terminal-green) !important;
        color: black !important;
    }

    /* Cards / Expanders */
    .streamlit-expanderHeader {
        background-color: #1A1A1A !important;
        color: var(--terminal-green) !important;
        border: 1px solid var(--terminal-green) !important;
        border-radius: 0px !important;
    }

    /* Custom classes for TUI vibe */
    .tui-border {
        border: 1px solid var(--terminal-green);
        padding: 20px;
        margin-bottom: 20px;
    }

    .tui-label {
        color: var(--terminal-amber);
        font-weight: bold;
    }

    .status-log {
        background-color: #111;
        border-left: 3px solid var(--terminal-green);
        padding: 10px;
        margin: 5px 0;
        font-size: 0.9em;
        color: var(--terminal-green);
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
    }
    ::-webkit-scrollbar-track {
        background: #0A0A0A;
    }
    ::-webkit-scrollbar-thumb {
        background: var(--terminal-green);
    }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO ---
@st.cache_resource
def startup():
    init_db()

startup()

# --- INTERFACE ---
st.markdown('<div class="tui-border">', unsafe_allow_html=True)
st.title("🔬 SRPESQUISAS v0.1.0_PROD")
st.write("SISTEMA DE MONITORAMENTO E SCOUT ACADÊMICO DE ALTA PRECISÃO")
st.markdown('</div>', unsafe_allow_html=True)

query = st.text_input("QUERY_STRING >", placeholder="Digite o composto ou tema de pesquisa...")

if st.button("EXECUTAR BUSCA") and query:
    st.markdown("---")
    
    # Area de Logs e Telemetria
    log_container = st.container()
    results_container = st.container()
    
    with log_container:
        st.subheader("PIPELINE_TELEMETRY")
        status_area = st.empty()
        # Dicionário para manter o histórico de logs na tela
        if 'log_history' not in st.session_state:
            st.session_state.log_history = []
        st.session_state.log_history = [] # Limpa para nova busca

    try:
        inputs = {"query": query}
        final_articles = []
        
        # Mapeamento de nós do Grafo
        node_map = {
            "query_planner": "🧠 Planejamento de Busca (LLM)",
            "search": "🌐 Buscando em Google Scholar & OpenAlex",
            "fetch_full_texts": "📄 Extraindo Metadados e Abstracts",
            "vision_extraction": "👁️ Analisando Gráficos (Vision)",
            "ranking": "⚖️ Ranqueamento por Relevância (LLM 70B)",
            "summarise": "📝 Gerando Resumos Executivos",
            "persist": "💾 Persistindo em Banco de Dados"
        }

        # Streaming do LangGraph
        for output in research_graph.stream(inputs):
            for node_name, values in output.items():
                display_name = node_map.get(node_name, node_name.upper())
                st.session_state.log_history.append(f"> {display_name} : OK")
                
                # Atualiza a área de status com todos os logs acumulados
                status_html = "".join([f'<div class="status-log">{log}</div>' for log in st.session_state.log_history])
                status_area.markdown(status_html, unsafe_allow_html=True)
                
                # Captura dados conforme aparecem no fluxo
                if "enriched_articles" in values:
                    final_articles = values["enriched_articles"]
                elif "ranked_articles" in values and not final_articles:
                    final_articles = values["ranked_articles"]
                elif "search_result" in values and not final_articles:
                    # Fallback caso pare antes do ranking/summarise
                    if hasattr(values["search_result"], "articles"):
                        final_articles = values["search_result"].articles

        # Exibição dos Resultados
        with results_container:
            st.markdown("---")
            st.success("ANÁLISE FINALIZADA COM SUCESSO.")
            
            if not final_articles:
                st.warning("AVISO: NENHUM DADO ENCONTRADO PARA A QUERY INFORMADA.")
            else:
                st.subheader(f"RESULTADOS: {len(final_articles)} ARTIGOS IDENTIFICADOS")
                
                for i, art in enumerate(final_articles, 1):
                    with st.expander(f"[{i:02d}] {art.title.upper()}"):
                        st.markdown(f'<span class="tui-label">ANO:</span> {art.year or "N/A"}', unsafe_allow_html=True)
                        st.markdown(f'<span class="tui-label">CITAÇÕES:</span> {art.citation_count}', unsafe_allow_html=True)
                        st.markdown(f'<span class="tui-label">DOI:</span> {art.doi or "N/A"}', unsafe_allow_html=True)
                        st.markdown(f'<span class="tui-label">LOCAL:</span> {art.venue or "N/A"}', unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown('<span class="tui-label">ANÁLISE IA (RESUMO/RELEVÂNCIA):</span>', unsafe_allow_html=True)
                        st.write(art.ai_summary or art.relevance_rationale or "Análise pendente.")
                        
                        st.markdown("---")
                        st.markdown('<span class="tui-label">ABSTRACT:</span>', unsafe_allow_html=True)
                        st.write(art.abstract or "Resumo indisponível.")

    except Exception as e:
        st.error(f"ERRO CRÍTICO NO SISTEMA: {str(e)}")
        st.session_state.log_history.append(f"!! FALHA NO NÓ: {str(e)}")
        status_html = "".join([f'<div class="status-log" style="color:red">{log}</div>' for log in st.session_state.log_history])
        status_area.markdown(status_html, unsafe_allow_html=True)

# --- FOOTER ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div style="text-align: center; color: #555; font-size: 0.8em;">'
            'SISTEMA OPERACIONAL SRPESQUISAS // GPU: NVIDIA H200 (141GB) // AGENTS: LANGGRAPH'
            '</div>', unsafe_allow_html=True)
