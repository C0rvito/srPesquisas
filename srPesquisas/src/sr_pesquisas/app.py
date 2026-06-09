import streamlit as st
import time
from sr_pesquisas.agents.pipeline import run_pipeline
from sr_pesquisas.database.engine import init_db
from sr_pesquisas.ui.tracer import tracer

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

col1, col2 = st.columns([1, 4])
with col1:
    search_btn = st.button("EXECUTAR BUSCA")

if search_btn and query:
    st.markdown("---")
    with st.status("ESTABELECENDO CONEXÃO COM O CORE ANALYTICS...", expanded=True) as status:
        st.write("Iniciando Pipeline de Inteligência...")
        try:
            # Captura o início do tempo para mostrar um "feeling" de terminal
            start_time = time.time()
            
            # Executa o Pipeline real
            final_state = run_pipeline(query)
            
            elapsed = time.time() - start_time
            status.update(label=f"BUSCA CONCLUÍDA EM {elapsed:.2f}s", state="complete", expanded=False)
            
            articles = (
                final_state.get("enriched_articles") or 
                final_state.get("ranked_articles") or 
                []
            )

            if not articles:
                st.warning("AVISO: NENHUM DADO ENCONTRADO PARA A QUERY INFORMADA.")
            else:
                st.subheader(f"RESULTADOS: {len(articles)} ARTIGOS IDENTIFICADOS")
                
                for i, art in enumerate(articles, 1):
                    with st.expander(f"[{i:02d}] {art.title.upper()}"):
                        st.markdown(f'<span class="tui-label">ANO:</span> {art.year or "N/A"}', unsafe_allow_html=True)
                        st.markdown(f'<span class="tui-label">CITAÇÕES:</span> {art.citation_count}', unsafe_allow_html=True)
                        st.markdown(f'<span class="tui-label">DOI:</span> {art.doi or "N/A"}', unsafe_allow_html=True)
                        st.markdown(f'<span class="tui-label">LOCAL:</span> {art.venue or "N/A"}', unsafe_allow_html=True)
                        
                        st.markdown("---")
                        st.markdown('<span class="tui-label">ANÁLISE IA (RELEVÂNCIA):</span>', unsafe_allow_html=True)
                        st.write(art.relevance_rationale or "Processando justificativa...")
                        
                        st.markdown("---")
                        st.markdown('<span class="tui-label">ABSTRACT:</span>', unsafe_allow_html=True)
                        st.write(art.abstract or "Resumo indisponível.")

        except Exception as e:
            st.error(f"ERRO CRÍTICO NO SISTEMA: {str(e)}")
            status.update(label="FALHA NA OPERAÇÃO", state="error")

# --- FOOTER ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div style="text-align: center; color: #555; font-size: 0.8em;">'
            'SISTEMA OPERACIONAL SRPESQUISAS // KERNEL: PYTHON 3.12 // AGENTS: LANGGRAPH'
            '</div>', unsafe_allow_html=True)
